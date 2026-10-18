import pytest
from unittest.mock import MagicMock, patch
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.core.config import settings
from backend.app.data.scenarios import get_scenario, reset_all_scenarios
from backend.app.services.tools.investigation_tools import (
    get_failure_details,
    get_recent_commits,
    get_workflow_definition,
    get_dependency_info,
    inspect_commit,
)
from backend.app.services.graph.graph_engine import CausalGraphEngine
from backend.app.services.agent.agent_service import AgentOrchestrator
from backend.app.services.verification.verifier import VerificationEngine
from backend.app.schemas.investigation import (
    StartInvestigationRequest,
    ApplyRemediationRequest,
    InvestigationReportModel
)


@pytest.fixture(autouse=True)
def reset_fixtures():
    reset_all_scenarios()
    yield
    reset_all_scenarios()


@pytest.fixture
def client():
    return TestClient(app)


# 1. Health endpoint
def test_health_endpoint(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "healthy"
    assert "mode" in data
    assert "gemini_model" in data


# 2. Scenario retrieval
def test_scenario_retrieval(client):
    response = client.get("/api/scenarios")
    assert response.status_code == 200
    scenarios = response.json()
    assert len(scenarios) >= 2
    scenario_ids = [s["id"] for s in scenarios]
    assert "scenario-invoice-field-rename" in scenario_ids
    assert "scenario-ambiguous-timeout" in scenario_ids


# 3. Failure details tool
def test_failure_details_tool():
    res = get_failure_details("scenario-invoice-field-rename")
    assert res["status"] == "success"
    assert res["failure_id"] == "FAIL-9021"
    assert "customer_email" in res["error_message"]
    assert res["affected_component"] == "invoice-generator"


# 4. Recent commits tool
def test_recent_commits_tool():
    res = get_recent_commits("scenario-invoice-field-rename", limit=3)
    assert res["status"] == "success"
    assert len(res["commits"]) >= 1
    commit_hashes = [c["commit_id"] for c in res["commits"]]
    assert "4f8a12d" in commit_hashes


# 5. Workflow definition tool
def test_workflow_definition_tool():
    res = get_workflow_definition("scenario-invoice-field-rename")
    assert res["status"] == "success"
    assert res["workflow_id"] == "wf-invoice-gen-v2"
    steps = res["steps"]
    assert len(steps) == 4
    step_3 = next(s for s in steps if s["step_id"] == "step_3")
    assert step_3["expected_field"] == "customer_email"


# 6. Dependency information tool
def test_dependency_info_tool():
    res = get_dependency_info("scenario-invoice-field-rename")
    assert res["status"] == "success"
    assert res["workflow_id"] == "wf-invoice-gen-v2"
    contracts = res["field_contracts"]
    assert len(contracts) > 0
    assert contracts[0]["field_name"] == "customer_email"


# 7. Commit inspection tool
def test_inspect_commit_tool():
    res = inspect_commit("scenario-invoice-field-rename", "4f8a12d")
    assert res["status"] == "success"
    assert res["commit_id"] == "4f8a12d"
    assert "services/customer/api.py" in res["file"]
    assert "-        \"customer_email\": customer.email," in res["diff"]
    assert "+        \"email\": customer.email," in res["diff"]


# 8. Invalid tool arguments
def test_invalid_tool_arguments():
    # Non-existent scenario
    res_bad_scenario = get_failure_details("non-existent-scenario")
    assert "error" in res_bad_scenario

    # Invalid empty arguments
    res_empty = get_failure_details("")
    assert "error" in res_empty

    # Unknown commit
    res_bad_commit = inspect_commit("scenario-invoice-field-rename", "unknown_hash_999")
    assert res_bad_commit["status"] == "error"


# 9. Agent iteration limit
def test_agent_iteration_limit():
    orchestrator = AgentOrchestrator()
    orchestrator.max_iterations = 2
    orchestrator.max_tool_calls = 10

    # Mock Gemini client to simulate an infinite tool-calling loop
    with patch("backend.app.services.agent.agent_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat

        # Model repeatedly asks for get_failure_details
        mock_call = MagicMock()
        mock_call.name = "get_failure_details"
        mock_call.args = {"scenario_id": "scenario-invoice-field-rename"}

        mock_resp = MagicMock()
        mock_resp.function_calls = [mock_call]
        mock_chat.send_message.return_value = mock_resp

        mock_client_cls.return_value = mock_client

        with patch.object(settings, "gemini_api_key", "test_key_fake"):
            report, events, _ = orchestrator._run_gemini_agent_loop(
                investigation_id="INV-TEST-LIMIT",
                scenario_id="scenario-invoice-field-rename",
                scenario=get_scenario("scenario-invoice-field-rename")
            )
            # Must stop gracefully at max_iterations
            assert report is not None
            tool_call_events = [e for e in events if e.type == "tool_call"]
            assert len(tool_call_events) <= 2


# 10. Tool-call limit
def test_tool_call_limit():
    orchestrator = AgentOrchestrator()
    orchestrator.max_iterations = 10
    orchestrator.max_tool_calls = 1

    with patch("backend.app.services.agent.agent_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat

        mock_call = MagicMock()
        mock_call.name = "get_failure_details"
        mock_call.args = {"scenario_id": "scenario-invoice-field-rename"}

        mock_resp = MagicMock()
        mock_resp.function_calls = [mock_call]
        mock_chat.send_message.return_value = mock_resp

        mock_client_cls.return_value = mock_client

        with patch.object(settings, "gemini_api_key", "test_key_fake"):
            report, events, _ = orchestrator._run_gemini_agent_loop(
                investigation_id="INV-TEST-TOOL-LIMIT",
                scenario_id="scenario-invoice-field-rename",
                scenario=get_scenario("scenario-invoice-field-rename")
            )
            assert report is not None
            tool_call_events = [e for e in events if e.type == "tool_call"]
            assert len(tool_call_events) <= 1


# 11. Invalid model-generated data (e.g., model requests a non-existent tool name)
def test_invalid_model_generated_data():
    orchestrator = AgentOrchestrator()

    with patch("backend.app.services.agent.agent_service.genai.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_chat = MagicMock()
        mock_client.chats.create.return_value = mock_chat

        mock_bad_call = MagicMock()
        mock_bad_call.name = "execute_arbitrary_shell_command"
        mock_bad_call.args = {"cmd": "rm -rf /"}

        mock_resp_1 = MagicMock()
        mock_resp_1.function_calls = [mock_bad_call]
        mock_resp_2 = MagicMock()
        mock_resp_2.function_calls = []

        mock_chat.send_message.side_effect = [mock_resp_1, mock_resp_2]
        mock_client_cls.return_value = mock_client

        with patch.object(settings, "gemini_api_key", "test_key_fake"):
            report, events, _ = orchestrator._run_gemini_agent_loop(
                investigation_id="INV-BAD-DATA",
                scenario_id="scenario-invoice-field-rename",
                scenario=get_scenario("scenario-invoice-field-rename")
            )
            # Backend safely refused unknown tool call and recorded error result
            result_events = [e for e in events if e.type == "tool_result"]
            assert any("Unknown tool" in str(e.tool_result) for e in result_events)


# 12. Missing Gemini configuration
def test_missing_gemini_configuration():
    orchestrator = AgentOrchestrator()
    with patch.object(settings, "gemini_api_key", None):
        report, events = orchestrator.run_investigation(
            investigation_id="INV-NO-KEY",
            scenario_id="scenario-invoice-field-rename"
        )
        assert report.mode == "DETERMINISTIC DEMO MODE"
        assert report.status == "completed"
        assert len(events) > 0
        assert not any(e.is_gemini_native for e in events)


# 13. Gemini API failure handling
def test_gemini_api_failure_handling():
    orchestrator = AgentOrchestrator()
    with patch("backend.app.services.agent.agent_service.genai.Client", side_effect=Exception("ResourceExhausted: 429 Quota Exceeded")):
        with patch.object(settings, "gemini_api_key", "valid_looking_key"):
            report, events = orchestrator.run_investigation(
                investigation_id="INV-QUOTA-FAIL",
                scenario_id="scenario-invoice-field-rename"
            )
            assert report.mode == "DETERMINISTIC DEMO MODE"
            # Recorded fallback event
            error_events = [e for e in events if e.type == "error"]
            assert len(error_events) >= 1
            assert "DETERMINISTIC DEMO MODE" in error_events[0].message


# 14. Evidence reference validation
def test_evidence_reference_validation():
    scenario = get_scenario("scenario-invoice-field-rename")
    orchestrator = AgentOrchestrator()
    report, _ = orchestrator.run_investigation(
        investigation_id="INV-EVID-VAL",
        scenario_id="scenario-invoice-field-rename",
        force_deterministic=True
    )
    evidence_ids = {e.id for e in report.evidence}
    # Check that root cause references existing evidence
    for ref_id in report.root_cause.evidence_ids:
        assert ref_id in evidence_ids, f"Referenced evidence ID {ref_id} must exist in report evidence list"


# 15. Graph construction
def test_graph_construction():
    graph = CausalGraphEngine.build_graph_for_scenario("scenario-invoice-field-rename")
    assert len(graph.nodes) == 4
    assert len(graph.edges) == 3

    node_types = {n.data.component_type for n in graph.nodes}
    assert "commit" in node_types
    assert "api_schema" in node_types
    assert "workflow_step" in node_types
    assert "failure" in node_types

    edge_relationships = {e.relationship for e in graph.edges}
    assert "modified" in edge_relationships
    assert "incompatible_with" in edge_relationships
    assert "contributed_to" in edge_relationships


# 16. Missing graph node references (validation prevents disconnected / broken edge references)
def test_missing_graph_node_references():
    graph = CausalGraphEngine.build_graph_for_scenario("scenario-invoice-field-rename")
    node_ids = {n.id for n in graph.nodes}
    for edge in graph.edges:
        assert edge.source in node_ids, f"Edge source {edge.source} must exist in nodes"
        assert edge.target in node_ids, f"Edge target {edge.target} must exist in nodes"


# 17. Simulated successful remediation
def test_simulated_successful_remediation(client):
    # Option A: Update workflow field mapping to 'email'
    res = VerificationEngine.verify_remediation(
        scenario_id="scenario-invoice-field-rename",
        option_id="opt-workflow-update"
    )
    assert res.status == "passed"
    assert res.simulated is True
    assert "SIMULATED VERIFICATION" in res.notice
    assert "successfully consumed field 'email'" in res.message


# 18. Simulated unsuccessful remediation
def test_simulated_unsuccessful_remediation(client):
    # Option C: Restarting worker does not resolve schema field missing
    res = VerificationEngine.verify_remediation(
        scenario_id="scenario-invoice-field-rename",
        option_id="opt-restart-worker"
    )
    assert res.status == "failed"
    assert res.simulated is True
    assert "recurred upon execution" in res.message


# 19. Unresolved root-cause behavior (ambiguous scenario returns unconfirmed root cause)
def test_unresolved_root_cause_behavior():
    orchestrator = AgentOrchestrator()
    report, _ = orchestrator.run_investigation(
        investigation_id="INV-AMB",
        scenario_id="scenario-ambiguous-timeout",
        force_deterministic=True
    )
    assert report.status == "unresolved"
    assert report.root_cause.status == "unconfirmed"
    assert report.root_cause.confidence_label == "Unconfirmed / Insufficient Evidence"
    assert len(report.remaining_unknowns) > 0


# 20. Demo reset behavior
def test_demo_reset_behavior(client):
    # Start an investigation
    resp = client.post(
        "/api/investigations",
        json={"scenario_id": "scenario-invoice-field-rename", "force_deterministic": True}
    )
    assert resp.status_code == 201
    inv_id = resp.json()["investigation_id"]

    # Mutate state by applying remediation
    rem_resp = client.post(
        f"/api/investigations/{inv_id}/remediation",
        json={"option_id": "opt-workflow-update"}
    )
    assert rem_resp.status_code == 200
    assert rem_resp.json()["verification"]["status"] == "passed"

    # Reset demo
    reset_resp = client.post("/api/demo/reset")
    assert reset_resp.status_code == 200
    assert reset_resp.json()["status"] == "success"

    # Verify investigation record was cleared
    get_resp = client.get(f"/api/investigations/{inv_id}")
    assert get_resp.status_code == 404
