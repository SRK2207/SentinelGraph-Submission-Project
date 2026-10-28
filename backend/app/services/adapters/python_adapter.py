from backend.app.services.security.execution_sandbox import SecureSubprocessRunner
import os
import re
import sys
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from backend.app.services.adapters.base import BaseEcosystemAdapter
from backend.app.services.stack.stack_detector import ProjectStackMetadata


class PythonAdapter(BaseEcosystemAdapter):
    """
    Adapter for Python projects using pytest or unittest runners.
    """

    def can_handle(self, metadata: ProjectStackMetadata) -> bool:
        return (
            metadata.primary_language == "python"
            or metadata.is_python
            or "python" in metadata.detected_languages
        ) and not (metadata.is_gradle or metadata.is_android)

    def discover_tests(
        self,
        project_id: str,
        src_dir: Path,
        metadata: ProjectStackMetadata
    ) -> Dict[str, Any]:
        test_files = metadata.test_files
        framework = "pytest"
        suggested = "pytest"

        return {
            "status": "success",
            "project_id": project_id,
            "ecosystem": "python",
            "test_framework": framework,
            "suggested_command": suggested,
            "total_test_files": len(test_files),
            "test_files": test_files
        }

    def execute_diagnostics(
        self,
        project_id: str,
        src_dir: Path,
        metadata: ProjectStackMetadata,
        test_command: Optional[str] = None,
        test_path: Optional[str] = None,
        timeout_seconds: int = 25
    ) -> Dict[str, Any]:
        # Formulate Python test command
        cmd = [sys.executable, "-m", "pytest", "-v"]

        custom_cmd = test_command.strip() if test_command else ""
        if custom_cmd.startswith("unittest") or "unittest" in custom_cmd:
            cmd = [sys.executable, "-m", "unittest", "discover", "-v"]
        elif test_path:
            # Append target file
            clean_path = Path(test_path).as_posix()
            cmd.append(clean_path)

        start_t = time.time()
        extra_env = {
            "PYTHONPATH": str(src_dir),
            "PYTHONDONTWRITEBYTECODE": "1"
        }

        try:
            exit_code, combined_output, timed_out = SecureSubprocessRunner.execute(
                cmd=cmd,
                cwd=src_dir,
                extra_env=extra_env,
                timeout_seconds=timeout_seconds
            )
            duration = round(time.time() - start_t, 3)

            if timed_out:
                return {
                    "status": "error",
                    "ecosystem": "python",
                    "project_id": project_id,
                    "error": f"Test execution timed out after {timeout_seconds} seconds.",
                    "passed": False,
                    "exit_code": -1,
                    "duration_seconds": duration,
                    "output": combined_output
                }

            passed = (exit_code == 0)
            tests_passed = None
            tests_failed = None
            if "passed" in combined_output or "failed" in combined_output:
                p_match = re.search(r"(\d+)\s+passed", combined_output)
                f_match = re.search(r"(\d+)\s+failed", combined_output)
                if p_match:
                    tests_passed = int(p_match.group(1))
                if f_match:
                    tests_failed = int(f_match.group(1))

            return {
                "status": "success",
                "ecosystem": "python",
                "project_id": project_id,
                "command": " ".join([Path(cmd[0]).name] + cmd[1:]),
                "exit_code": exit_code,
                "passed": passed,
                "duration_seconds": duration,
                "tests_passed": tests_passed,
                "tests_failed": tests_failed,
                "output": combined_output,
                "message": "Tests passed successfully." if passed else "Tests failed with errors."
            }
        except Exception as e:
            return {
                "status": "error",
                "ecosystem": "python",
                "project_id": project_id,
                "error": f"Failed to execute Python tests: {str(e)}",
                "passed": False,
                "exit_code": 1
            }
