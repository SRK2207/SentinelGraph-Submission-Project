import os
import sys
import pytest
from pathlib import Path

from backend.app.services.security.execution_sandbox import (
    SecureSubprocessRunner,
    get_host_security_profile,
    DEFAULT_MAX_OUTPUT_BYTES
)
from backend.app.services.workspace.workspace_manager import (
    workspace_manager,
    WorkspaceSecurityError
)
from backend.app.services.tools.workspace_tools import (
    edit_file,
    revert_file,
    read_file
)
from backend.app.services.agent.agent_service import AgentOrchestrator


def test_env_sanitization_strips_gemini_key_and_secrets():
    """
    Verify that sensitive environment variables (such as GEMINI_API_KEY, tokens, credentials)
    are strictly scrubbed and never leak to subprocess child environments.
    """
    dirty_env = {
        "PATH": os.environ.get("PATH", ""),
        "SYSTEMROOT": os.environ.get("SYSTEMROOT", r"C:\Windows"),
        "GEMINI_API_KEY": "AIzaSy_SUPER_SECRET_LEAK_TEST_KEY_12345",
        "API_SECRET_TOKEN": "shhh-dont-leak-me",
        "AWS_SECRET_ACCESS_KEY": "wJalrXUtnFEMI/K7MDENG/bPxRfiCYEXAMPLEKEY",
        "DATABASE_PASSWORD": "root_password_production",
        "SAFE_CUSTOM_CONFIG": "safe_value"
    }

    clean_env = SecureSubprocessRunner.sanitize_environment(base_env=dirty_env)

    # Strictly forbidden keys must not be present
    assert "GEMINI_API_KEY" not in clean_env
    assert "API_SECRET_TOKEN" not in clean_env
    assert "AWS_SECRET_ACCESS_KEY" not in clean_env
    assert "DATABASE_PASSWORD" not in clean_env

    # Run real subprocess using Python to probe its own os.environ
    script = (
        "import os\n"
        "has_gemini = 'GEMINI_API_KEY' in os.environ\n"
        "has_secret = 'API_SECRET_TOKEN' in os.environ\n"
        "print(f'GEMINI_LEAKED:{has_gemini}, SECRET_LEAKED:{has_secret}')\n"
    )

    cwd = Path(__file__).resolve().parent
    # Inject test env through os.environ temporarily to verify runner purges it
    orig_key = os.environ.get("GEMINI_API_KEY")
    try:
        os.environ["GEMINI_API_KEY"] = "AIzaSy_LEAK_CANARY_VALUE"
        code, output, timed_out = SecureSubprocessRunner.execute(
            cmd=[sys.executable, "-c", script],
            cwd=cwd,
            timeout_seconds=5
        )
        assert code == 0
        assert not timed_out
        assert "GEMINI_LEAKED:False" in output
        assert "SECRET_LEAKED:False" in output
    finally:
        if orig_key is not None:
            os.environ["GEMINI_API_KEY"] = orig_key
        else:
            os.environ.pop("GEMINI_API_KEY", None)


def test_output_size_cap_prevents_memory_dos():
    """
    Verify that huge stdout/stderr streams are truncated cleanly to prevent memory exhaustion DoS.
    """
    # Generate 500,000 characters
    script = "import sys; sys.stdout.write('A' * 500000)"
    cwd = Path(__file__).resolve().parent

    code, output, timed_out = SecureSubprocessRunner.execute(
        cmd=[sys.executable, "-c", script],
        cwd=cwd,
        max_output_bytes=4096,  # 4 KB cap for test
        timeout_seconds=5
    )

    assert code == 0
    assert not timed_out
    assert len(output) < 10000
    assert "SECURITY NOTICE: Output exceeded 4096 bytes cap" in output


def test_timeout_process_tree_termination():
    """
    Verify that processes exceeding timeout are killed reliably and reported with timeout status.
    """
    script = "import time; time.sleep(10)"
    cwd = Path(__file__).resolve().parent

    code, output, timed_out = SecureSubprocessRunner.execute(
        cmd=[sys.executable, "-c", script],
        cwd=cwd,
        timeout_seconds=1
    )

    assert timed_out is True
    assert code == -1
    assert "SECURITY NOTICE: Execution timed out after 1s" in output


def test_filesystem_path_traversal_rejection_in_workspace():
    """
    Verify that resolving paths with directory traversal sequences strictly raises WorkspaceSecurityError.
    """
    proj_id = "sample-broken-invoice-project"

    with pytest.raises(WorkspaceSecurityError) as exc_info:
        workspace_manager.resolve_safe_path(proj_id, "../../Windows/System32/cmd.exe")
    assert "Path traversal detected" in str(exc_info.value)

    with pytest.raises(WorkspaceSecurityError) as exc_info_abs:
        workspace_manager.resolve_safe_path(proj_id, "C:/Windows/System32/calc.exe")
    assert "Path traversal detected" in str(exc_info_abs.value)


def test_snapshot_immutability():
    """
    Verify that editing files in the workspace (src/) NEVER alters the original snapshot.
    """
    proj_id = "sample-broken-invoice-project"
    workspace_manager.reset_project(proj_id)

    orig_dir = workspace_manager.get_original_dir(proj_id)
    orig_content_before = (orig_dir / "invoice_worker.py").read_text(encoding="utf-8")

    # Edit src/ file
    edit_res = edit_file(
        project_id=proj_id,
        file_path="invoice_worker.py",
        target="recipient_email = profile['customer_email']",
        replacement="recipient_email = 'MUTATED_VALUE_FOR_TEST'"
    )
    assert edit_res["status"] == "success"

    # Verify src/ changed
    src_read = read_file(proj_id, "invoice_worker.py")
    assert "MUTATED_VALUE_FOR_TEST" in src_read["content"]

    # Verify original/ remains untouched!
    orig_content_after = (orig_dir / "invoice_worker.py").read_text(encoding="utf-8")
    assert orig_content_before == orig_content_after
    assert "MUTATED_VALUE_FOR_TEST" not in orig_content_after

    # Revert back
    revert_file(proj_id, "invoice_worker.py")
    workspace_manager.reset_project(proj_id)


def test_execution_security_profile_reporting():
    """
    Verify that the host security profile reports honest capabilities and does not falsely claim containerization.
    """
    profile = get_host_security_profile()
    # On Windows without Docker:
    assert profile.secret_scrubbing_enabled is True
    assert profile.process_tree_termination is True
    assert profile.output_size_cap_bytes == DEFAULT_MAX_OUTPUT_BYTES

    if not profile.container_isolated:
        assert profile.sandbox_mode == "HOST_PROCESS_RESTRICTED"
        assert any("Docker/WSL are not installed" in limit for limit in profile.known_limitations)
