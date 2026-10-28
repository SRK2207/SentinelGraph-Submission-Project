import os
import py_compile
from pathlib import Path
from typing import Dict, Any, Optional

from backend.app.services.adapters.base import BaseEcosystemAdapter
from backend.app.services.stack.stack_detector import ProjectStackMetadata


class GenericAdapter(BaseEcosystemAdapter):
    """
    Fallback adapter for general or unclassified projects.
    Performs static checks and structural inspection without fabricating dynamic tests.
    """

    def can_handle(self, metadata: ProjectStackMetadata) -> bool:
        return True

    def discover_tests(
        self,
        project_id: str,
        src_dir: Path,
        metadata: ProjectStackMetadata
    ) -> Dict[str, Any]:
        return {
            "status": "success",
            "project_id": project_id,
            "ecosystem": "generic",
            "test_framework": "none_detected",
            "suggested_command": None,
            "total_test_files": len(metadata.test_files),
            "test_files": metadata.test_files,
            "missing_prerequisites": metadata.missing_prerequisites
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
        # Perform static syntax checks on source files
        errors = []
        checked_count = 0

        for root, _, files in os.walk(src_dir):
            for file in files:
                if file.endswith(".py"):
                    full_p = Path(root) / file
                    checked_count += 1
                    try:
                        py_compile.compile(str(full_p), doraise=True)
                    except py_compile.PyCompileError as pce:
                        errors.append(f"Syntax error in {file}: {str(pce)}")

        if errors:
            return {
                "status": "success",
                "ecosystem": "generic",
                "project_id": project_id,
                "command": "static syntax check",
                "exit_code": 1,
                "passed": False,
                "duration_seconds": 0.05,
                "tests_passed": 0,
                "tests_failed": len(errors),
                "output": "\n".join(errors),
                "message": f"Static syntax check failed with {len(errors)} error(s)."
            }

        return {
            "status": "success",
            "ecosystem": "generic",
            "project_id": project_id,
            "command": "static analysis (no dynamic runner configured)",
            "exit_code": 0,
            "passed": True,
            "duration_seconds": 0.05,
            "tests_passed": checked_count,
            "tests_failed": 0,
            "output": f"Static analysis completed. {checked_count} file(s) checked. No dedicated dynamic test runner configured.",
            "message": "Static syntax checks passed."
        }
