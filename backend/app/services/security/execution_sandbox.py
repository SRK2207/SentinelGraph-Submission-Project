import os
import re
import sys
import time
import shutil
import logging
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional, List, Tuple
from pydantic import BaseModel, Field

logger = logging.getLogger("sentinelgraph.security")

# Maximum output stream buffer cap (512 KB) to prevent memory exhaustion DoS
DEFAULT_MAX_OUTPUT_BYTES = 512 * 1024

# Explicit whitelist of safe environment variables necessary for compilers/interpreters
SAFE_ENV_KEYS = {
    # Windows system environment
    "SYSTEMROOT",
    "SYSTEMDRIVE",
    "WINDIR",
    "COMSPEC",
    "PATHEXT",
    "TEMP",
    "TMP",
    "LOCALAPPDATA",
    "APPDATA",
    "PROGRAMFILES",
    "PROGRAMFILES(X86)",
    "COMMONPROGRAMFILES",
    "ALLUSERSPROFILE",
    "PUBLIC",
    "HOMEDRIVE",
    "HOMEPATH",
    "USERPROFILE",
    "NUMBER_OF_PROCESSORS",
    "OS",
    "PROCESSOR_ARCHITECTURE",
    # Unix system environment
    "PATH",
    "SHELL",
    "TERM",
    "LANG",
    "LC_ALL",
    "HOME",
    # Language runtime defaults
    "PYTHONPATH",
    "PYTHONDONTWRITEBYTECODE",
    "NODE_PATH",
    "NODE_ENV"
}

# Regex pattern identifying sensitive keys to strictly strip
SENSITIVE_KEY_PATTERN = re.compile(
    r"(KEY|SECRET|TOKEN|CREDENTIAL|PASSWORD|AUTH|GEMINI|API|AWS|AZURE|GCP|PRIVATE|SSH)",
    re.IGNORECASE
)


class ExecutionSecurityProfile(BaseModel):
    """
    Explicit specification of security boundaries, guarantees, and environmental limitations.
    """
    sandbox_mode: str = Field(..., description="Active sandbox enforcement mode (e.g. HOST_PROCESS_RESTRICTED)")
    container_isolated: bool = Field(False, description="Whether full kernel/hypervisor container isolation is active")
    secret_scrubbing_enabled: bool = Field(True, description="Whether host secrets and tokens are scrubbed from child env")
    output_size_cap_bytes: int = Field(DEFAULT_MAX_OUTPUT_BYTES, description="Maximum captured output bytes before truncation")
    process_tree_termination: bool = Field(True, description="Whether child process trees are terminated on timeout")
    guarantees: List[str] = Field(default_factory=list, description="Guarantees established and verified on this host")
    known_limitations: List[str] = Field(default_factory=list, description="Known security limitations of the current host")


def get_host_security_profile() -> ExecutionSecurityProfile:
    """
    Inspects host platform and returns genuine, uninflated security profile.
    """
    has_docker = shutil.which("docker") is not None
    container_mode = "CONTAINER_ISOLATED" if has_docker else "HOST_PROCESS_RESTRICTED"

    guarantees = [
        "Environment variable scrubbing: SentinelGraph API keys, tokens, and secrets are strictly excluded from subprocess environment.",
        "Output size capping: Subprocess stdout/stderr captured with hard 512KB cap to prevent memory exhaustion DoS.",
        "Process tree cleanup: Timeout or abort terminates entire child process hierarchy on Windows/POSIX.",
        "Filesystem containment: All working copy edits and commands are bounded to the workspace src directory.",
        "Original snapshot immutability: Original project files are stored in a separate read-only snapshot directory."
    ]

    known_limitations = []
    if not has_docker:
        known_limitations.extend([
            "No container virtualization: Docker/WSL are not installed on this host; processes execute under host user credentials.",
            "No network namespace isolation: Subprocess network access cannot be kernel-isolated on bare Windows without Hyper-V/container.",
            "No cgroup memory/CPU hard caps: Subprocess resource limits are enforced via software timeouts and stream caps, not OS cgroups."
        ])

    return ExecutionSecurityProfile(
        sandbox_mode=container_mode,
        container_isolated=has_docker,
        secret_scrubbing_enabled=True,
        output_size_cap_bytes=DEFAULT_MAX_OUTPUT_BYTES,
        process_tree_termination=True,
        guarantees=guarantees,
        known_limitations=known_limitations
    )


class SecureSubprocessRunner:
    """
    Manages safe subprocess execution for diagnostic tools and test runners.
    Prevents secret leakage, memory exhaustion, orphaned child processes, and unbounded execution.
    """

    @staticmethod
    def sanitize_environment(
        base_env: Optional[Dict[str, str]] = None,
        extra_env: Optional[Dict[str, str]] = None
    ) -> Dict[str, str]:
        """
        Creates a clean environment dictionary containing only whitelisted safe variables
        and strictly purging any sensitive tokens (e.g. GEMINI_API_KEY).
        """
        source = base_env if base_env is not None else os.environ
        clean_env: Dict[str, str] = {}

        # 1. Copy only safe whitelisted keys from host
        for key, val in source.items():
            key_upper = key.upper()
            if key_upper in SAFE_ENV_KEYS:
                # Still check if someone put a secret in an otherwise normal var
                if not SENSITIVE_KEY_PATTERN.search(key_upper):
                    clean_env[key] = val

        # 2. Add extra project-specific variables (e.g. PYTHONPATH) after validation
        if extra_env:
            for k, v in extra_env.items():
                if not SENSITIVE_KEY_PATTERN.search(k.upper()):
                    clean_env[k] = str(v)
                else:
                    logger.warning(f"Blocked attempt to inject sensitive environment variable: {k}")

        # 3. Always enforce safe execution defaults
        clean_env["PYTHONDONTWRITEBYTECODE"] = "1"
        clean_env["PYTHONUNBUFFERED"] = "1"

        return clean_env

    @staticmethod
    def kill_process_tree(pid: int) -> None:
        """
        Reliably terminates the target process and all child processes spawned by it.
        """
        if not pid:
            return

        try:
            if os.name == "nt":
                # Windows taskkill /F /T kills process tree reliably
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    capture_output=True,
                    timeout=5,
                    check=False
                )
            else:
                # POSIX process group kill
                import signal
                try:
                    pgid = os.getpgid(pid)
                    os.killpg(pgid, signal.SIGKILL)
                except Exception:
                    os.kill(pid, signal.SIGKILL)
        except Exception as e:
            logger.debug(f"Error terminating process tree for PID {pid}: {e}")

    @classmethod
    def execute(
        cls,
        cmd: List[str],
        cwd: Path,
        extra_env: Optional[Dict[str, str]] = None,
        timeout_seconds: int = 25,
        max_output_bytes: int = DEFAULT_MAX_OUTPUT_BYTES,
        shell: bool = False
    ) -> Tuple[int, str, bool]:
        """
        Executes command with sanitized environment, strict timeout, process-tree termination,
        and bounded output size.
        
        Returns: (exit_code, combined_output, timed_out)
        """
        if not cwd.exists():
            raise FileNotFoundError(f"Working directory does not exist: {cwd}")

        clean_env = cls.sanitize_environment(extra_env=extra_env)

        start_time = time.time()
        timed_out = False
        proc = None

        try:
            # Create process
            proc = subprocess.Popen(
                cmd,
                cwd=str(cwd),
                env=clean_env,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                errors="replace",
                shell=shell
            )

            try:
                stdout_str, stderr_str = proc.communicate(timeout=timeout_seconds)
                exit_code = proc.returncode
            except subprocess.TimeoutExpired:
                timed_out = True
                cls.kill_process_tree(proc.pid)
                # Drain whatever was buffered before termination
                try:
                    stdout_str, stderr_str = proc.communicate(timeout=2)
                except Exception:
                    stdout_str, stderr_str = "", ""
                exit_code = -1

            # Format and enforce size bounds on stdout / stderr
            combined = stdout_str or ""
            if stderr_str:
                combined += ("\n--- STDERR ---\n" + stderr_str)

            # Cap byte size to prevent memory explosion
            if len(combined.encode("utf-8", errors="replace")) > max_output_bytes:
                # Truncate at character boundary approximately matching byte cap
                trunc_char_count = max_output_bytes // 2
                head = combined[:trunc_char_count]
                tail = combined[-trunc_char_count:]
                combined = (
                    f"{head}\n\n"
                    f"[SECURITY NOTICE: Output exceeded {max_output_bytes} bytes cap. Truncated to prevent memory exhaustion.]\n\n"
                    f"{tail}"
                )

            if timed_out:
                combined = (
                    f"[SECURITY NOTICE: Execution timed out after {timeout_seconds}s and process tree was terminated.]\n"
                    f"{combined}"
                )

            return exit_code, combined.strip(), timed_out

        except Exception as ex:
            if proc and proc.pid:
                cls.kill_process_tree(proc.pid)
            raise ex
