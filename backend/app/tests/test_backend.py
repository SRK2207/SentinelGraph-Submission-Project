import io
import sys
import zipfile
import pytest
from typing import Any
from unittest.mock import MagicMock, patch
from fastapi import HTTPException

from backend.app.core.config import settings
from backend.app.services.workspace.workspace_manager import workspace_manager, WorkspaceSecurityError
from backend.app.services.tools.workspace_tools import (
    list_project_files,
    search_code,
    read_file,
    inspect_dependencies,
    discover_tests_and_commands,
    run_tests,
    edit_file,
    write_file,
    revert_file,
    get_workspace_diff,
)
from backend.app.services.graph.graph_engine import CausalGraphEngine
from backend.app.services.agent.agent_service import AgentOrchestrator
from backend.app.schemas.investigation import StartInvestigationRequest
from backend.app.api import endpoints


def run_sync(coro):
    try:
        coro.send(None)
    except StopIteration as e:
        return e.value


class MockResponse:
    def __init__(self, status_code: int, data: Any):
        self.status_code = status_code
        self._data = data

    def json(self):
        if hasattr(self._data, "model_dump"):
            return self._data.model_dump()
        elif isinstance(self._data, list):
            return [item.model_dump() if hasattr(item, "model_dump") else item for item in self._data]
        return self._data


class DirectApiClient:
    def get(self, url: str):
        if url == "/api/health":
            data = endpoints.get_health()
            return MockResponse(200, data)
        elif url == "/api/dashboard":
            data = endpoints.get_dashboard()
            return MockResponse(200, data)
        elif url == "/api/connections":
            data = endpoints.get_connections()
            return MockResponse(200, data)
        elif url == "/api/projects":
            data = endpoints.list_projects()
            return MockResponse(200, data)
        elif url.startswith("/api/projects/") and url.endswith("/diff"):
            parts = url.split("/")
            pid = parts[3]
            try:
                data = endpoints.get_project_diff(pid)
                return MockResponse(200, data)
            except HTTPException as e:
                return MockResponse(e.status_code, {"detail": e.detail})
        elif url.startswith("/api/projects/"):
            parts = url.split("/")
            pid = parts[3]
            try:
                data = endpoints.get_project(pid)
                return MockResponse(200, data)
            except HTTPException as e:
                return MockResponse(e.status_code, {"detail": e.detail})
        raise NotImplementedError(f"Route not handled in DirectApiClient: {url}")

    def post(self, url: str, json: Any = None, files: Any = None):
        if url == "/api/projects/sample":
            data = endpoints.create_sample_project()
            return MockResponse(201, data)
        elif url == "/api/projects/upload":
            file_tuple = files.get("file")
            filename, content, ctype = file_tuple

            class UploadAdapter:
                def __init__(self, fn, ct):
                    self.filename = fn
                    self.ct = ct
                async def read(self):
                    return self.ct

            try:
                data = run_sync(endpoints.upload_project(UploadAdapter(filename, content)))
                return MockResponse(201, data)
            except HTTPException as e:
                return MockResponse(e.status_code, {"detail": e.detail})
        elif url == "/api/investigations":
            req = StartInvestigationRequest(**(json or {}))
            try:
                data = endpoints.start_investigation(req)
                return MockResponse(200, data)
            except HTTPException as e:
                return MockResponse(e.status_code, {"detail": e.detail})
        elif url.endswith("/reset"):
            parts = url.split("/")
            pid = parts[3]
            try:
                data = endpoints.reset_project(pid)
                return MockResponse(200, data)
            except HTTPException as e:
                return MockResponse(e.status_code, {"detail": e.detail})
        elif url.endswith("/run-tests"):
            parts = url.split("/")
            pid = parts[3]
            try:
                data = endpoints.execute_project_tests(pid)
                return MockResponse(200, data)
            except HTTPException as e:
                return MockResponse(e.status_code, {"detail": e.detail})
        raise NotImplementedError(f"Route not handled in DirectApiClient: {url}")


@pytest.fixture(autouse=True)
def clean_workspaces():
    # Setup sample project
    meta = workspace_manager.create_sample_broken_project()
    yield meta
    # Cleanup / reset
    try:
        workspace_manager.reset_project(meta["project_id"])
    except Exception:
        pass


@pytest.fixture
def client():
    return DirectApiClient()


# 1. Health endpoint
def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "version" in data
    assert "mode" in data
    assert "gemini_configured" in data


# 2. Dashboard endpoint
def test_dashboard_endpoint(client):
    response = client.get("/api/dashboard")
    assert response.status_code == 200
    data = response.json()
    assert "total_investigations" in data
    assert "uploaded_projects" in data
    assert "mode_available" in data


# 3. Connections endpoint
def test_connections_endpoint(client):
    response = client.get("/api/connections")
    assert response.status_code == 200
    conns = response.json()
    assert len(conns) >= 2
    conn_ids = [c["id"] for c in conns]
    assert "conn-workspace-fs" in conn_ids
    assert "conn-subprocess-runner" in conn_ids


# 4. Sample project creation
def test_sample_project_creation(client):
    response = client.post("/api/projects/sample")
    assert response.status_code == 201
    data = response.json()
    assert data["project_id"] == "sample-broken-invoice-project"
    assert data["file_count"] >= 4
    assert "customer_service.py" in data["files"]
    assert "test_invoice_worker.py" in data["files"]


# 5. Project listing & retrieval
def test_project_listing_and_retrieval(client):
    response = client.get("/api/projects")
    assert response.status_code == 200
    projects = response.json()
    assert len(projects) >= 1
    sample_id = projects[0]["project_id"]

    get_resp = client.get(f"/api/projects/{sample_id}")
    assert get_resp.status_code == 200
    assert get_resp.json()["project_id"] == sample_id


# 6. Safe ZIP extraction & path traversal rejection
def test_zip_upload_and_path_traversal_protection(client):
    # Test valid zip upload
    valid_zip_buf = io.BytesIO()
    with zipfile.ZipFile(valid_zip_buf, "w") as zf:
        zf.writestr("module.py", "def add(a, b): return a + b\n")
        zf.writestr("test_module.py", "from module import add\ndef test_add(): assert add(1, 2) == 3\n")

    valid_zip_buf.seek(0)
    upload_resp = client.post(
        "/api/projects/upload",
        files={"file": ("valid_project.zip", valid_zip_buf.getvalue(), "application/zip")}
    )
    assert upload_resp.status_code == 201
    proj_id = upload_resp.json()["project_id"]
    assert upload_resp.json()["file_count"] == 2

    # Test malicious zip upload with path traversal entry (../../evil.txt)
    evil_zip_buf = io.BytesIO()
    with zipfile.ZipFile(evil_zip_buf, "w") as zf:
        zf.writestr("../../evil.txt", "MALICIOUS CONTENT")
    evil_zip_buf.seek(0)

    evil_resp = client.post(
        "/api/projects/upload",
        files={"file": ("evil_project.zip", evil_zip_buf.getvalue(), "application/zip")}
    )
    assert evil_resp.status_code == 400
    assert "Path traversal attempt detected" in evil_resp.json()["detail"]


# 7. Workspace Tool: list_project_files
def test_tool_list_project_files():
    res = list_project_files("sample-broken-invoice-project")
    assert res["status"] == "success"
    file_paths = [f["path"] for f in res["files"]]
    assert "customer_service.py" in file_paths
    assert "test_invoice_worker.py" in file_paths


# 8. Workspace Tool: search_code
def test_tool_search_code():
    res = search_code("sample-broken-invoice-project", query="customer_email")
    assert res["status"] == "success"
    assert res["total_matches"] >= 1
    matching_files = [m["file"] for m in res["matches"]]
    assert "invoice_worker.py" in matching_files


# 9. Workspace Tool: read_file & path traversal block
def test_tool_read_file_and_traversal_block():
    # Valid read
    res = read_file("sample-broken-invoice-project", "customer_service.py", start_line=1, end_line=5)
    assert res["status"] == "success"
    assert res["start_line"] == 1
    assert "CustomerService" in res["content"]

    # Block path traversal
    bad_res = read_file("sample-broken-invoice-project", "../../etc/passwd")
    assert bad_res["status"] == "error"
    assert "Path traversal detected" in bad_res["error"]


# 10. Workspace Tool: inspect_dependencies
def test_tool_inspect_dependencies():
    res = inspect_dependencies("sample-broken-invoice-project")
    assert res["status"] == "success"
    assert "requirements.txt" in res["manifests_found"]
    assert any("pytest" in req for req in res["dependencies"]["requirements.txt"])


# 11. Workspace Tool: discover_tests_and_commands
def test_tool_discover_tests_and_commands():
    res = discover_tests_and_commands("sample-broken-invoice-project")
    assert res["status"] == "success"
    assert res["test_framework"] == "pytest"
    assert "test_invoice_worker.py" in res["test_files"]


# 12. Workspace Tool: run_tests (baseline fails before fix)
def test_tool_run_tests_baseline_fails():
    res = run_tests("sample-broken-invoice-project")
    assert res["status"] == "success"
    assert res["passed"] is False
    assert res["exit_code"] != 0
    # Must capture the actual KeyError failure
    assert "KeyError" in res["output"]
    assert "customer_email" in res["output"]


# 13. Workspace Tool: edit_file (applies real repair to source code)
def test_tool_edit_file():
    proj_id = "sample-broken-invoice-project"
    # The defect is that invoice_worker expects 'customer_email', but customer_service returned 'email'
    target = "recipient_email = profile['customer_email']"
    replacement = "recipient_email = profile.get('customer_email') or profile.get('email')"

    edit_res = edit_file(proj_id, "invoice_worker.py", target=target, replacement=replacement)
    assert edit_res["status"] == "success"

    # Read back to verify modification on disk
    read_back = read_file(proj_id, "invoice_worker.py")
    assert replacement in read_back["content"]


# 14. Workspace Tool: run_tests (passes after fix!)
def test_tool_run_tests_passes_after_repair():
    proj_id = "sample-broken-invoice-project"
    # Apply fix
    target = "recipient_email = profile['customer_email']"
    replacement = "recipient_email = profile.get('customer_email') or profile.get('email')"
    edit_file(proj_id, "invoice_worker.py", target=target, replacement=replacement)

    # Re-run real tests
    test_res = run_tests(proj_id)
    assert test_res["status"] == "success"
    assert test_res["passed"] is True
    assert test_res["exit_code"] == 0
    assert "2 passed" in test_res["output"]


# 15. Workspace Tool: get_workspace_diff
def test_tool_get_workspace_diff():
    proj_id = "sample-broken-invoice-project"
    target = "recipient_email = profile['customer_email']"
    replacement = "recipient_email = profile.get('customer_email') or profile.get('email')"
    edit_file(proj_id, "invoice_worker.py", target=target, replacement=replacement)

    diff_res = get_workspace_diff(proj_id)
    assert diff_res["status"] == "success"
    assert "invoice_worker.py" in diff_res["changed_files"]
    assert "-    recipient_email = profile['customer_email']" in diff_res["diff"]
    assert "+    recipient_email = profile.get('customer_email') or profile.get('email')" in diff_res["diff"]


# 16. Workspace Tool: revert_file
def test_tool_revert_file():
    proj_id = "sample-broken-invoice-project"
    workspace_manager.reset_project(proj_id)
    target = "recipient_email = profile['customer_email']"
    replacement = "recipient_email = 'HARDCODED_EMAIL'"
    edit_res = edit_file(proj_id, "invoice_worker.py", target=target, replacement=replacement)
    assert edit_res["status"] == "success"

    revert_res = revert_file(proj_id, "invoice_worker.py")
    assert revert_res["status"] == "success"

    read_back = read_file(proj_id, "invoice_worker.py")
    assert "recipient_email = profile['customer_email']" in read_back["content"]


# 17. Agent: Missing API key returns explicit error (NO simulation fallback)
def test_agent_missing_api_key_explicit_error():
    orchestrator = AgentOrchestrator()
    with patch.object(settings, "gemini_api_key", None):
        with pytest.raises(ValueError) as excinfo:
            orchestrator.run_project_investigation(
                investigation_id="INV-NO-KEY",
                project_id="sample-broken-invoice-project"
            )
        assert "Gemini API key is not configured" in str(excinfo.value)
        assert "Automatic simulation fallback has been disabled" in str(excinfo.value)


# 18. API Endpoint: Missing API key returns HTTP 400 Bad Request
def test_api_missing_api_key_returns_400(client):
    with patch.object(settings, "gemini_api_key", None):
        resp = client.post(
            "/api/investigations",
            json={"project_id": "sample-broken-invoice-project"}
        )
        assert resp.status_code == 400
        assert "Gemini API key is not configured" in resp.json()["detail"]


# 19. Agent Mocked Tool-Calling Loop with Real Workspace Repair
def test_agent_mock_tool_loop_executes_real_repair():
    orchestrator = AgentOrchestrator()
    proj_id = "sample-broken-invoice-project"
    workspace_manager.reset_project(proj_id)

    try:
        with patch("backend.app.services.agent.agent_service.genai.Client") as mock_client_cls:
            mock_client = MagicMock()
            mock_chat = MagicMock()
            mock_client.chats.create.return_value = mock_chat

            # Turn 1: Model calls run_tests
            call_1 = MagicMock()
            call_1.name = "run_tests"
            call_1.args = {"project_id": proj_id}
            resp_1 = MagicMock()
            resp_1.function_calls = [call_1]

            # Turn 2: Model calls edit_file to fix KeyError
            call_2 = MagicMock()
            call_2.name = "edit_file"
            call_2.args = {
                "project_id": proj_id,
                "file_path": "invoice_worker.py",
                "target": "recipient_email = profile['customer_email']",
                "replacement": "recipient_email = profile.get('customer_email') or profile.get('email')"
            }
            resp_2 = MagicMock()
            resp_2.function_calls = [call_2]

            # Turn 3: Model calls run_tests again to verify
            call_3 = MagicMock()
            call_3.name = "run_tests"
            call_3.args = {"project_id": proj_id}
            resp_3 = MagicMock()
            resp_3.function_calls = [call_3]

            # Turn 4: Model finishes
            resp_4 = MagicMock()
            resp_4.function_calls = []
            resp_4.text = "Fixed KeyError by reading email key from profile payload. Verified all tests pass."

            mock_chat.send_message.side_effect = [resp_1, resp_2, resp_3, resp_4]
            mock_client_cls.return_value = mock_client

            with patch.object(settings, "gemini_api_key", "test_key_live"):
                report, events = orchestrator.run_project_investigation(
                    investigation_id="INV-MOCK-LIVE",
                    project_id=proj_id
                )

                # Verification must be REAL and passed!
                assert report.status == "completed"
                assert report.verification.status == "passed"
                assert report.verification.simulated is False
                assert "REAL VERIFICATION" in report.verification.notice
                assert report.verification.exit_code == 0
                assert "invoice_worker.py" in report.changed_files
                assert report.diff is not None
                assert len(events) >= 5
    finally:
        workspace_manager.reset_project(proj_id)


# 20. Project Graph Generation
def test_project_graph_generation():
    graph = CausalGraphEngine.build_graph_for_project(
        project_id="sample-broken-invoice-project",
        changed_files=["invoice_worker.py"],
        test_passed=True
    )
    assert len(graph.nodes) >= 4
    assert len(graph.edges) >= 3

    node_ids = {n.id for n in graph.nodes}
    assert "node-source-file" in node_ids
    assert "node-test-file" in node_ids
    assert "node-failure-event" in node_ids
    assert "node-repair-patch" in node_ids


# 21. Project Reset API endpoint
def test_project_reset_endpoint(client):
    proj_id = "sample-broken-invoice-project"
    # Make a change
    edit_file(proj_id, "invoice_worker.py", "recipient_email", "MODIFIED_TEXT")

    # Reset via API
    resp = client.post(f"/api/projects/{proj_id}/reset")
    assert resp.status_code == 200
    assert resp.json()["status"] == "success"

    # Verify original file content is restored
    read_back = read_file(proj_id, "invoice_worker.py")
    assert "recipient_email = profile['customer_email']" in read_back["content"]


# 22. End-to-End Project Workflow API Test
def test_end_to_end_project_workflow_api(client):
    # 1. Run baseline tests via API
    test_resp = client.post("/api/projects/sample-broken-invoice-project/run-tests")
    assert test_resp.status_code == 200
    assert test_resp.json()["passed"] is False

    # 2. Get initial diff (empty)
    diff_resp = client.get("/api/projects/sample-broken-invoice-project/diff")
    assert diff_resp.status_code == 200
    assert diff_resp.json()["total_changed_files"] == 0

    # 3. Apply a real fix using edit_file tool
    edit_file(
        "sample-broken-invoice-project",
        "invoice_worker.py",
        "recipient_email = profile['customer_email']",
        "recipient_email = profile.get('customer_email') or profile.get('email')"
    )

    # 4. Run tests again via API (must pass!)
    test_resp_2 = client.post("/api/projects/sample-broken-invoice-project/run-tests")
    assert test_resp_2.status_code == 200
    assert test_resp_2.json()["passed"] is True
    assert test_resp_2.json()["exit_code"] == 0

    # 5. Get diff via API (shows unified diff of the fix)
    diff_resp_2 = client.get("/api/projects/sample-broken-invoice-project/diff")
    assert diff_resp_2.status_code == 200
    assert diff_resp_2.json()["total_changed_files"] == 1
    assert "invoice_worker.py" in diff_resp_2.json()["changed_files"]
