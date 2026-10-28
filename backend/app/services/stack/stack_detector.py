import os
import shutil
from pathlib import Path
from typing import Dict, Any, List, Optional, Set
from pydantic import BaseModel, Field


class ProjectStackMetadata(BaseModel):
    primary_language: str = "unknown"
    detected_languages: List[str] = Field(default_factory=list)
    build_systems: List[str] = Field(default_factory=list)
    test_frameworks: List[str] = Field(default_factory=list)
    is_android: bool = False
    is_gradle: bool = False
    is_node: bool = False
    is_python: bool = False
    available_runners: List[str] = Field(default_factory=list)
    missing_prerequisites: List[str] = Field(default_factory=list)
    suggested_command: Optional[str] = None
    confidence: float = 1.0
    summary: str = ""
    manifest_files: List[str] = Field(default_factory=list)
    source_files_sample: List[str] = Field(default_factory=list)
    test_files: List[str] = Field(default_factory=list)


IGNORED_DIRS = {
    ".git", "__pycache__", "venv", ".venv", "node_modules",
    ".pytest_cache", ".next", "dist", "build", ".gradle", ".idea"
}

EXTENSION_MAP = {
    ".py": "python",
    ".kt": "kotlin",
    ".kts": "kotlin",
    ".java": "java",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".rs": "rust",
    ".go": "go",
    ".c": "c",
    ".cpp": "c++",
    ".h": "c/c++",
    ".cs": "csharp",
    ".rb": "ruby",
    ".php": "php"
}


class StackDetector:
    """
    Evidence-based technology stack and ecosystem detector.
    Analyzes project root directory, manifests, build scripts, file extensions,
    and checks host executable availability to determine diagnostic strategy.
    """

    @classmethod
    def detect_path(cls, root_dir: Path) -> ProjectStackMetadata:
        """
        Inspect the given directory path and return structured stack metadata.
        """
        if not root_dir.exists() or not root_dir.is_dir():
            return ProjectStackMetadata(
                primary_language="unknown",
                summary="Target directory does not exist or is not a directory."
            )

        manifests_found: List[str] = []
        extension_counts: Dict[str, int] = {}
        all_files: List[str] = []
        test_files: List[str] = []

        # Traverse directory
        for root, dirs, files in os.walk(root_dir):
            dirs[:] = [d for d in dirs if d not in IGNORED_DIRS]
            for file in files:
                full_path = Path(root) / file
                rel_path = full_path.relative_to(root_dir).as_posix()
                all_files.append(rel_path)

                ext = full_path.suffix.lower()
                if ext in EXTENSION_MAP:
                    lang = EXTENSION_MAP[ext]
                    extension_counts[lang] = extension_counts.get(lang, 0) + 1

                # Check for manifest indicators
                file_lower = file.lower()
                if file_lower in {
                    "requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "pipfile",
                    "package.json", "package-lock.json", "yarn.lock", "pnpm-lock.yaml", "tsconfig.json",
                    "build.gradle", "build.gradle.kts", "settings.gradle", "settings.gradle.kts",
                    "pom.xml", "gradlew", "gradlew.bat", "androidmanifest.xml",
                    "cargo.toml", "go.mod"
                }:
                    manifests_found.append(rel_path)

                # Check for test files
                if (
                    file.startswith("test_")
                    or file.endswith("_test.py")
                    or "tests/" in rel_path.lower()
                    or "test/" in rel_path.lower()
                    or file.endswith(".test.js")
                    or file.endswith(".test.ts")
                    or file.endswith(".spec.js")
                    or file.endswith(".spec.ts")
                    or file.endswith("Test.kt")
                    or file.endswith("Test.java")
                    or file.endswith("Tests.kt")
                    or file.endswith("Tests.java")
                ):
                    test_files.append(rel_path)

        # Detect Build Systems & Frameworks
        build_systems: Set[str] = set()
        test_frameworks: Set[str] = set()
        detected_languages: Set[str] = set(extension_counts.keys())

        has_py_manifest = any(m in manifests_found for m in ["requirements.txt", "pyproject.toml", "setup.py", "setup.cfg", "Pipfile"])
        has_node_manifest = any(m in manifests_found for m in ["package.json", "tsconfig.json"])
        has_gradle_manifest = any("build.gradle" in m or "settings.gradle" in m for m in manifests_found)
        has_maven_manifest = any("pom.xml" in m for m in manifests_found)
        has_android_manifest = any("androidmanifest.xml" in m.lower() for m in manifests_found) or any("app/build.gradle" in m for m in manifests_found)
        has_cargo_manifest = any("cargo.toml" in m.lower() for m in manifests_found)
        has_go_manifest = any("go.mod" in m.lower() for m in manifests_found)

        is_android = has_android_manifest
        is_gradle = has_gradle_manifest
        is_node = has_node_manifest
        is_python = has_py_manifest or ("python" in detected_languages and not (has_node_manifest or has_gradle_manifest))

        if is_gradle:
            build_systems.add("gradle")
            if "kotlin" in detected_languages or any("build.gradle.kts" in m for m in manifests_found):
                detected_languages.add("kotlin")
            if "java" in detected_languages:
                detected_languages.add("java")
            if is_android:
                test_frameworks.add("android-junit")
                test_frameworks.add("gradle-test")
            else:
                test_frameworks.add("junit")
                test_frameworks.add("gradle-test")

        if is_node:
            build_systems.add("npm")
            if "typescript" in detected_languages or any("tsconfig.json" in m for m in manifests_found):
                detected_languages.add("typescript")
            else:
                detected_languages.add("javascript")
            test_frameworks.add("npm-test")

        if is_python:
            build_systems.add("pip")
            detected_languages.add("python")
            test_frameworks.add("pytest")

        if has_cargo_manifest or "rust" in detected_languages:
            build_systems.add("cargo")
            detected_languages.add("rust")
            test_frameworks.add("cargo-test")

        if has_go_manifest or "go" in detected_languages:
            build_systems.add("go-modules")
            detected_languages.add("go")
            test_frameworks.add("go-test")

        # Determine Primary Language by ranking priority:
        # If Android/Gradle: Kotlin or Java
        # Else dominant by file count
        primary_lang = "unknown"
        if is_android or is_gradle:
            if extension_counts.get("kotlin", 0) >= extension_counts.get("java", 0):
                primary_lang = "kotlin" if extension_counts.get("kotlin", 0) > 0 or any(".kts" in m for m in manifests_found) else "java"
            else:
                primary_lang = "java"
        elif is_node:
            primary_lang = "typescript" if extension_counts.get("typescript", 0) >= extension_counts.get("javascript", 0) and extension_counts.get("typescript", 0) > 0 else "javascript"
        elif is_python:
            primary_lang = "python"
        elif extension_counts:
            # Sort by count
            sorted_langs = sorted(extension_counts.items(), key=lambda x: x[1], reverse=True)
            primary_lang = sorted_langs[0][0]

        # Host Tool Availability & Prerequisite Check
        available_runners: List[str] = []
        missing_prerequisites: List[str] = []

        has_python_cmd = shutil.which("python") is not None or shutil.which("python3") is not None
        has_pytest_cmd = shutil.which("pytest") is not None or has_python_cmd  # can run python -m pytest
        has_node_cmd = shutil.which("node") is not None
        has_npm_cmd = shutil.which("npm") is not None
        has_system_gradle = shutil.which("gradle") is not None
        has_wrapper_gradle = (root_dir / "gradlew").exists() or (root_dir / "gradlew.bat").exists()
        has_java_cmd = shutil.which("java") is not None
        has_android_sdk = (
            os.environ.get("ANDROID_HOME") is not None
            or os.environ.get("ANDROID_SDK_ROOT") is not None
        )

        suggested_command = None

        if primary_lang == "python" or is_python:
            if has_pytest_cmd:
                available_runners.append("pytest")
                available_runners.append("unittest")
                suggested_command = "pytest"
            else:
                missing_prerequisites.append("Python pytest runtime not installed on host")

        elif is_gradle or is_android or primary_lang in {"kotlin", "java"}:
            if has_wrapper_gradle or has_system_gradle:
                runner = "./gradlew test" if (root_dir / "gradlew").exists() else ("gradlew.bat test" if (root_dir / "gradlew.bat").exists() else "gradle test")
                available_runners.append(runner)
                suggested_command = runner
            else:
                missing_prerequisites.append("Gradle build tool / wrapper not found in project or host")

            if is_android and not has_android_sdk:
                missing_prerequisites.append("Android SDK environment (ANDROID_HOME/ANDROID_SDK_ROOT) not configured on host")

        elif is_node or primary_lang in {"javascript", "typescript"}:
            if has_npm_cmd:
                available_runners.append("npm test")
                suggested_command = "npm test"
            else:
                missing_prerequisites.append("Node.js / npm not installed on host system")

        elif primary_lang == "rust":
            if shutil.which("cargo"):
                available_runners.append("cargo test")
                suggested_command = "cargo test"
            else:
                missing_prerequisites.append("Cargo / Rust toolchain not installed on host")

        elif primary_lang == "go":
            if shutil.which("go"):
                available_runners.append("go test ./...")
                suggested_command = "go test ./..."
            else:
                missing_prerequisites.append("Go compiler runtime not installed on host")

        # Human-readable summary
        summary_parts = []
        if is_android:
            summary_parts.append(f"Android application ({primary_lang.title()})")
        else:
            summary_parts.append(f"{primary_lang.title()} project")

        if build_systems:
            summary_parts.append(f"Build System: {', '.join(sorted(build_systems))}")
        if test_frameworks:
            summary_parts.append(f"Framework: {', '.join(sorted(test_frameworks))}")
        if missing_prerequisites:
            summary_parts.append(f"Prerequisite Alert: {'; '.join(missing_prerequisites)}")

        summary = " | ".join(summary_parts)

        return ProjectStackMetadata(
            primary_language=primary_lang,
            detected_languages=sorted(list(detected_languages)),
            build_systems=sorted(list(build_systems)),
            test_frameworks=sorted(list(test_frameworks)),
            is_android=is_android,
            is_gradle=is_gradle,
            is_node=is_node,
            is_python=is_python,
            available_runners=available_runners,
            missing_prerequisites=missing_prerequisites,
            suggested_command=suggested_command,
            confidence=0.95 if manifests_found else 0.70,
            summary=summary,
            manifest_files=manifests_found,
            source_files_sample=all_files[:15],
            test_files=test_files
        )

    @classmethod
    def detect_workspace(cls, project_id: str) -> ProjectStackMetadata:
        """
        Inspect project workspace by project_id using workspace_manager.
        """
        from backend.app.services.workspace.workspace_manager import workspace_manager
        src_dir = workspace_manager.get_src_dir(project_id)
        return cls.detect_path(src_dir)
