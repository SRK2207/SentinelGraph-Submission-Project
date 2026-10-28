import io
import os
import json
import zipfile
import pytest
from pathlib import Path
from unittest.mock import MagicMock, patch

from backend.app.services.stack.stack_detector import StackDetector, ProjectStackMetadata
from backend.app.services.adapters.registry import adapter_registry
from backend.app.services.adapters.gradle_adapter import GradleKotlinAdapter
from backend.app.services.adapters.python_adapter import PythonAdapter
from backend.app.services.adapters.node_adapter import NodeAdapter
from backend.app.services.adapters.generic_adapter import GenericAdapter
from backend.app.services.workspace.workspace_manager import workspace_manager
from backend.app.services.tools.workspace_tools import run_tests, discover_tests_and_commands, detect_project_stack
from backend.app.services.graph.graph_engine import CausalGraphEngine
from backend.app.services.investigations.investigation_manager import investigation_manager
from backend.app.schemas.investigation import StartInvestigationRequest
from backend.app.core.config import settings


@pytest.fixture
def temp_project_dir(tmp_path):
    yield tmp_path


# 1. Stack Detection: Python Project
def test_stack_detection_python(temp_project_dir):
    (temp_project_dir / "app.py").write_text("print('hello')", encoding="utf-8")
    (temp_project_dir / "requirements.txt").write_text("pytest>=8.0.0", encoding="utf-8")
    tests_dir = temp_project_dir / "tests"
    tests_dir.mkdir()
    (tests_dir / "test_app.py").write_text("def test_dummy(): assert True", encoding="utf-8")

    meta = StackDetector.detect_path(temp_project_dir)
    assert meta.primary_language == "python"
    assert meta.is_python is True
    assert meta.is_gradle is False
    assert meta.is_android is False
    assert "pytest" in meta.test_frameworks
    assert meta.suggested_command == "pytest"
    assert len(meta.test_files) == 1


# 2. Stack Detection: Node / TypeScript Project
def test_stack_detection_node_typescript(temp_project_dir):
    (temp_project_dir / "index.ts").write_text("console.log('ts')", encoding="utf-8")
    (temp_project_dir / "tsconfig.json").write_text("{}", encoding="utf-8")
    pkg_json = {
        "name": "my-node-app",
        "scripts": {"test": "jest"}
    }
    (temp_project_dir / "package.json").write_text(json.dumps(pkg_json), encoding="utf-8")
    (temp_project_dir / "index.test.ts").write_text("test('dummy', () => {});", encoding="utf-8")

    meta = StackDetector.detect_path(temp_project_dir)
    assert meta.primary_language == "typescript"
    assert meta.is_node is True
    assert meta.is_gradle is False
    assert meta.is_android is False
    assert "npm" in meta.build_systems
    assert meta.suggested_command == "npm test"
    assert len(meta.test_files) == 1


# 3. Stack Detection: Attendance Tracker (Kotlin / Gradle / Android)
def test_stack_detection_attendance_tracker_android_gradle(temp_project_dir):
    # Setup Attendance Tracker project structure
    (temp_project_dir / "build.gradle.kts").write_text("// Top-level build file", encoding="utf-8")
    (temp_project_dir / "settings.gradle.kts").write_text("rootProject.name = \"attendance-tracker\"", encoding="utf-8")
    
    app_dir = temp_project_dir / "app"
    app_dir.mkdir()
    (app_dir / "build.gradle.kts").write_text("plugins { id(\"com.android.application\") }", encoding="utf-8")
    
    main_dir = app_dir / "src" / "main"
    main_dir.mkdir(parents=True)
    (main_dir / "AndroidManifest.xml").write_text("<manifest package=\"com.attendance\"></manifest>", encoding="utf-8")
    
    kt_dir = main_dir / "java" / "com" / "attendance"
    kt_dir.mkdir(parents=True)
    (kt_dir / "MainActivity.kt").write_text("package com.attendance\nclass MainActivity", encoding="utf-8")

    test_dir = app_dir / "src" / "test" / "java" / "com" / "attendance"
    test_dir.mkdir(parents=True)
    (test_dir / "AttendanceTrackerTest.kt").write_text("package com.attendance\nclass AttendanceTrackerTest", encoding="utf-8")

    meta = StackDetector.detect_path(temp_project_dir)
    assert meta.primary_language == "kotlin"
    assert meta.is_android is True
    assert meta.is_gradle is True
    assert meta.is_python is False
    assert "gradle" in meta.build_systems
    assert any("junit" in f for f in meta.test_frameworks)
    assert len(meta.test_files) == 1


# 4. Diagnostic Adapter Selection: NEVER Route Gradle to Pytest
def test_adapter_selection_gradle_never_routes_to_pytest(temp_project_dir):
    (temp_project_dir / "build.gradle.kts").write_text("// gradle", encoding="utf-8")
    (temp_project_dir / "MainActivity.kt").write_text("class MainActivity", encoding="utf-8")

    meta = StackDetector.detect_path(temp_project_dir)
    adapter = adapter_registry.get_adapter(meta)

    # Must be GradleKotlinAdapter, NOT PythonAdapter!
    assert isinstance(adapter, GradleKotlinAdapter)
    assert not isinstance(adapter, PythonAdapter)

    disco = adapter.discover_tests("sample-id", temp_project_dir, meta)
    assert disco["ecosystem"] == "gradle/kotlin"
    assert disco["suggested_command"] != "pytest"
    assert "gradle" in disco["suggested_command"]


# 5. Missing Toolchain Prerequisite: Clean and Honest Limitation Handling
def test_gradle_missing_prerequisites_honest_reporting(temp_project_dir):
    (temp_project_dir / "build.gradle").write_text("// gradle", encoding="utf-8")
    (temp_project_dir / "MainActivity.kt").write_text("class MainActivity", encoding="utf-8")

    meta = StackDetector.detect_path(temp_project_dir)
    adapter = GradleKotlinAdapter()

    # When wrapper and system gradle are absent (or Android SDK missing)
    with patch("shutil.which", return_value=None):
        with patch.dict(os.environ, {}, clear=True):
            res = adapter.execute_diagnostics("proj-android-test", temp_project_dir, meta)

            assert res["status"] == "prerequisite_missing"
            assert res["passed"] is False
            assert res["exit_code"] is None
            assert "PREREQUISITE LIMITATION" in res["output"]
            assert "refuses to run unrelated test runners (such as pytest)" in res["output"]


# 6. Causal Graph Integrity: No Phantom "customer_service.py" on Attendance Tracker
def test_causal_graph_integrity_non_invoice_project():
    # Create an Attendance Tracker workspace in workspace_manager
    proj_id = "test-attendance-tracker"
    src_dir = workspace_manager.get_src_dir(proj_id)
    orig_dir = workspace_manager.get_original_dir(proj_id)
    src_dir.mkdir(parents=True, exist_ok=True)
    orig_dir.mkdir(parents=True, exist_ok=True)

    (src_dir / "build.gradle.kts").write_text("// build", encoding="utf-8")
    (src_dir / "MainActivity.kt").write_text("package com.attendance\nclass MainActivity", encoding="utf-8")
    (src_dir / "AndroidManifest.xml").write_text("<manifest></manifest>", encoding="utf-8")

    # Generate graph
    graph = CausalGraphEngine.build_graph_for_project(
        project_id=proj_id,
        changed_files=["MainActivity.kt"],
        test_passed=False
    )

    # Inspect all node labels and metadata
    for node in graph.nodes:
        # Crucial check: customer_service.py must NEVER be present!
        assert "customer_service.py" not in node.data.label
        assert node.data.metadata.get("file") != "customer_service.py"

    # Source node should reflect MainActivity.kt
    source_node = next((n for n in graph.nodes if n.id == "node-source-file"), None)
    assert source_node is not None
    assert "MainActivity.kt" in source_node.data.label

    # Test runner node should reflect Android/Gradle
    test_node = next((n for n in graph.nodes if n.id == "node-test-file"), None)
    assert test_node is not None
    assert "Android" in test_node.data.label or "Gradle" in test_node.data.label

    # Cleanup
    import shutil
    shutil.rmtree(workspace_manager.get_project_dir(proj_id), ignore_errors=True)


# 7. End-to-End Investigation Manager Pipeline on Kotlin/Android Project
def test_investigation_manager_attendance_tracker_fixture():
    # Build a simulated attendance tracker zip
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w") as zf:
        zf.writestr("build.gradle.kts", "// Top-level gradle")
        zf.writestr("settings.gradle.kts", "rootProject.name = 'attendance'")
        zf.writestr("AndroidManifest.xml", "<manifest package='com.attendance'></manifest>")
        zf.writestr("MainActivity.kt", "package com.attendance\nclass MainActivity")
        zf.writestr("AttendanceTest.kt", "package com.attendance\nclass AttendanceTest")

    # Upload zip via workspace_manager
    meta = workspace_manager.create_project_from_zip(zip_buffer.getvalue(), "attendance_tracker.zip")
    proj_id = meta["project_id"]

    try:
        # Verify stack metadata attached to uploaded project
        assert meta["stack"] is not None
        assert meta["stack"]["primary_language"] == "kotlin"
        assert meta["stack"]["is_android"] is True
        assert meta["stack"]["is_gradle"] is True

        # Run stack detection tool directly
        stack_res = detect_project_stack(proj_id)
        assert stack_res["status"] == "success"
        assert stack_res["primary_language"] == "kotlin"
        assert stack_res["is_android"] is True

        # Discover tests
        disco_res = discover_tests_and_commands(proj_id)
        assert disco_res["ecosystem"] == "gradle/kotlin"
        assert "pytest" not in disco_res.get("suggested_command", "")

        # Run diagnostic execution
        diag_res = run_tests(proj_id)
        # Should cleanly indicate prerequisite missing on machines without Android SDK
        if diag_res["status"] == "prerequisite_missing":
            assert diag_res["passed"] is False
            assert "Android SDK" in diag_res["output"] or "Gradle" in diag_res["output"]
            assert diag_res["exit_code"] is None

        # Build graph
        graph = CausalGraphEngine.build_graph_for_project(
            project_id=proj_id,
            changed_files=[],
            test_passed=False
        )
        assert all("customer_service.py" not in n.data.label for n in graph.nodes)

    finally:
        import shutil
        shutil.rmtree(workspace_manager.get_project_dir(proj_id), ignore_errors=True)
