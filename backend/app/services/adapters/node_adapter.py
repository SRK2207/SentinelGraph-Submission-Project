from backend.app.services.security.execution_sandbox import SecureSubprocessRunner
import os
import shutil
import time
import subprocess
import json
from pathlib import Path
from typing import Dict, Any, Optional

from backend.app.services.adapters.base import BaseEcosystemAdapter
from backend.app.services.stack.stack_detector import ProjectStackMetadata


class NodeAdapter(BaseEcosystemAdapter):
    """
    Adapter for Node.js, JavaScript, and TypeScript projects.
    """

    def can_handle(self, metadata: ProjectStackMetadata) -> bool:
        return (
            metadata.is_node
            or metadata.primary_language in {"javascript", "typescript"}
            or "javascript" in metadata.detected_languages
            or "typescript" in metadata.detected_languages
        ) and not (metadata.is_gradle or metadata.is_android)

    def discover_tests(
        self,
        project_id: str,
        src_dir: Path,
        metadata: ProjectStackMetadata
    ) -> Dict[str, Any]:
        pkg_file = src_dir / "package.json"
        scripts = {}
        if pkg_file.exists():
            try:
                pkg_data = json.loads(pkg_file.read_text(encoding="utf-8", errors="ignore"))
                scripts = pkg_data.get("scripts", {})
            except Exception:
                pass

        test_files = metadata.test_files
        framework = "npm test"
        if "test" in scripts:
            framework = scripts["test"]

        return {
            "status": "success",
            "project_id": project_id,
            "ecosystem": "node",
            "test_framework": framework,
            "suggested_command": "npm test",
            "package_scripts": scripts,
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
        has_npm = shutil.which("npm") is not None
        has_node = shutil.which("node") is not None

        if not has_npm or not has_node:
            err_msg = (
                f"ENVIRONMENT PREREQUISITE LIMITATION:\n"
                f"Project '{project_id}' is a Node.js / TypeScript project.\n"
                f"Node.js runtime or npm package manager is not installed on the host system.\n"
                f"SentinelGraph strictly refuses to run unrelated test runners or simulate test passes.\n"
                f"To run tests, install Node.js and npm on the host."
            )
            return {
                "status": "prerequisite_missing",
                "ecosystem": "node",
                "project_id": project_id,
                "command": "npm test (Node/npm unavailable)",
                "exit_code": None,
                "passed": False,
                "duration_seconds": 0.0,
                "tests_passed": 0,
                "tests_failed": 0,
                "output": err_msg,
                "message": "Node.js / npm not installed on host. Dynamic tests could not be executed.",
                "missing_prerequisites": ["node", "npm"]
            }

        cmd = ["npm", "test"]
        if test_command:
            parts = test_command.strip().split()
            if parts and ("npm" in parts[0] or "yarn" in parts[0] or "pnpm" in parts[0]):
                cmd = parts

        # On Windows, npm is npm.cmd
        if os.name == "nt" and cmd[0] == "npm":
            npm_cmd = shutil.which("npm.cmd") or "npm.cmd"
            cmd[0] = npm_cmd

        start_t = time.time()
        try:
            exit_code, combined_output, timed_out = SecureSubprocessRunner.execute(
                cmd=cmd,
                cwd=src_dir,
                timeout_seconds=timeout_seconds,
                shell=(os.name == "nt")
            )
            duration = round(time.time() - start_t, 3)

            if timed_out:
                return {
                    "status": "error",
                    "ecosystem": "node",
                    "project_id": project_id,
                    "error": f"Node test execution timed out after {timeout_seconds} seconds.",
                    "passed": False,
                    "exit_code": -1,
                    "duration_seconds": duration,
                    "output": combined_output
                }

            passed = (exit_code == 0)
            return {
                "status": "success",
                "ecosystem": "node",
                "project_id": project_id,
                "command": " ".join(cmd),
                "exit_code": exit_code,
                "passed": passed,
                "duration_seconds": duration,
                "tests_passed": None,
                "tests_failed": None,
                "output": combined_output,
                "message": "npm test passed successfully." if passed else "npm test failed."
            }
        except Exception as e:
            return {
                "status": "error",
                "ecosystem": "node",
                "project_id": project_id,
                "error": f"Failed to execute Node tests: {str(e)}",
                "passed": False,
                "exit_code": 1
            }
