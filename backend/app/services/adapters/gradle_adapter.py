import os
import shutil
import time
import subprocess
from pathlib import Path
from typing import Dict, Any, Optional

from backend.app.services.adapters.base import BaseEcosystemAdapter
from backend.app.services.stack.stack_detector import ProjectStackMetadata


class GradleKotlinAdapter(BaseEcosystemAdapter):
    """
    Adapter for Kotlin, Java, Gradle, and Android projects (e.g. Attendance Tracker).
    Ensures Gradle-based tasks are used and NEVER falls back to pytest.
    Accurately reports prerequisite limitations when Gradle or Android SDK are not on host.
    """

    def can_handle(self, metadata: ProjectStackMetadata) -> bool:
        return (
            metadata.is_gradle
            or metadata.is_android
            or metadata.primary_language in {"kotlin", "java"}
            or "kotlin" in metadata.detected_languages
            or "java" in metadata.detected_languages
        )

    def discover_tests(
        self,
        project_id: str,
        src_dir: Path,
        metadata: ProjectStackMetadata
    ) -> Dict[str, Any]:
        test_files = metadata.test_files
        framework = "android-junit" if metadata.is_android else "junit/gradle"
        suggested = metadata.suggested_command or "./gradlew test"

        return {
            "status": "success",
            "project_id": project_id,
            "ecosystem": "gradle/kotlin",
            "is_android": metadata.is_android,
            "test_framework": framework,
            "suggested_command": suggested,
            "total_test_files": len(test_files),
            "test_files": test_files,
            "missing_prerequisites": metadata.missing_prerequisites
        }

    def execute_diagnostics(
        self,
        project_id: str,
        src_dir: Path,
        metadata: ProjectStackMetadata,
        test_command: Optional[str] = None,
        test_path: Optional[str] = None,
        timeout_seconds: int = 30
    ) -> Dict[str, Any]:
        # Check for Gradle Wrapper or System Gradle
        gradlew_unix = src_dir / "gradlew"
        gradlew_bat = src_dir / "gradlew.bat"
        has_wrapper = gradlew_unix.exists() or gradlew_bat.exists()
        has_system_gradle = shutil.which("gradle") is not None

        # Check Android SDK if Android project
        has_android_sdk = (
            os.environ.get("ANDROID_HOME") is not None
            or os.environ.get("ANDROID_SDK_ROOT") is not None
        )

        # Detect if execution environment is missing required toolchains
        if not has_wrapper and not has_system_gradle:
            err_msg = (
                f"ENVIRONMENT PREREQUISITE LIMITATION:\n"
                f"Project '{project_id}' is detected as {metadata.primary_language.title()} / Gradle "
                f"({'Android' if metadata.is_android else 'JVM'}).\n"
                f"No Gradle build tool or wrapper was found in the workspace or host environment.\n"
                f"SentinelGraph strictly refuses to run unrelated test runners (such as pytest) or fabricate results.\n"
                f"To run tests for this project, provide a Gradle wrapper ('gradlew') or install Gradle on the host."
            )
            return {
                "status": "prerequisite_missing",
                "ecosystem": "gradle/kotlin",
                "project_id": project_id,
                "command": "gradle test (prerequisite unavailable)",
                "exit_code": None,
                "passed": False,
                "duration_seconds": 0.0,
                "tests_passed": 0,
                "tests_failed": 0,
                "output": err_msg,
                "message": "Gradle build tools not configured on host. Dynamic tests could not be executed.",
                "missing_prerequisites": ["gradle", "gradle-wrapper"]
            }

        if metadata.is_android and not has_android_sdk:
            err_msg = (
                f"ENVIRONMENT PREREQUISITE LIMITATION:\n"
                f"Project '{project_id}' is an Android application requiring Android SDK tools.\n"
                f"Neither 'ANDROID_HOME' nor 'ANDROID_SDK_ROOT' environment variables are configured on host.\n"
                f"SentinelGraph strictly refuses to run unrelated test runners or falsify results.\n"
                f"To verify Android tests, configure the Android SDK in the host environment."
            )
            return {
                "status": "prerequisite_missing",
                "ecosystem": "gradle/kotlin",
                "project_id": project_id,
                "command": "./gradlew test (Android SDK unavailable)",
                "exit_code": None,
                "passed": False,
                "duration_seconds": 0.0,
                "tests_passed": 0,
                "tests_failed": 0,
                "output": err_msg,
                "message": "Android SDK not configured on host. Android tests cannot be executed.",
                "missing_prerequisites": ["android-sdk"]
            }

        # Select executable command
        if os.name == "nt" and gradlew_bat.exists():
            cmd = [str(gradlew_bat), "test"]
        elif gradlew_unix.exists():
            cmd = [str(gradlew_unix), "test"]
        else:
            cmd = ["gradle", "test"]

        if test_command:
            parts = test_command.strip().split()
            if parts and ("gradle" in parts[0] or "gradlew" in parts[0]):
                cmd = parts

        start_t = time.time()
        try:
            proc = subprocess.run(
                cmd,
                cwd=str(src_dir),
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            duration = round(time.time() - start_t, 3)
            passed = (proc.returncode == 0)
            stdout = proc.stdout or ""
            stderr = proc.stderr or ""
            combined_output = (stdout + ("\n--- STDERR ---\n" + stderr if stderr else "")).strip()

            return {
                "status": "success",
                "ecosystem": "gradle/kotlin",
                "project_id": project_id,
                "command": " ".join(cmd),
                "exit_code": proc.returncode,
                "passed": passed,
                "duration_seconds": duration,
                "tests_passed": None,
                "tests_failed": None,
                "output": combined_output,
                "message": "Gradle tests passed successfully." if passed else "Gradle test execution failed."
            }
        except subprocess.TimeoutExpired:
            return {
                "status": "error",
                "ecosystem": "gradle/kotlin",
                "project_id": project_id,
                "error": f"Gradle execution timed out after {timeout_seconds} seconds.",
                "passed": False,
                "exit_code": -1,
                "output": f"Gradle task timed out after {timeout_seconds}s."
            }
        except Exception as e:
            return {
                "status": "error",
                "ecosystem": "gradle/kotlin",
                "project_id": project_id,
                "error": f"Failed to execute Gradle tests: {str(e)}",
                "passed": False,
                "exit_code": 1
            }
