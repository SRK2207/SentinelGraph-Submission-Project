import networkx as nx
from typing import Dict, Any, List, Optional
from backend.app.schemas.investigation import (
    GraphDataModel,
    GraphNodeModel,
    GraphEdgeModel,
    GraphNodePosition,
    GraphNodeData
)


class CausalGraphEngine:
    """
    Builds and processes causal dependency graphs using NetworkX.
    Translates directed graph representations into React Flow-compatible nodes and edges.
    """

    @staticmethod
    def build_graph_for_project(
        project_id: str,
        changed_files: Optional[List[str]] = None,
        test_passed: bool = True,
        evidence_list: Optional[List[Dict[str, Any]]] = None
    ) -> GraphDataModel:
        g = nx.DiGraph()
        files = changed_files or ["customer_service.py"]
        primary_file = files[0] if files else "source_code.py"
        ev_ids = [e.get("id", "") for e in (evidence_list or [])]

        # Node 1: Defective / Modified Source File
        g.add_node(
            "node-source-file",
            label=f"Source: {primary_file}",
            component_type="api_schema",
            status="probable_cause",
            explanation=f"Source file '{primary_file}' contained the defect breaking contract expectations.",
            evidence_ids=[eid for eid in ev_ids if "FILE" in eid or "PATCH" in eid],
            metadata={"file": primary_file}
        )

        # Node 2: Dependent / Test Consumer
        g.add_node(
            "node-test-file",
            label="Consumer / Test Suite",
            component_type="workflow_step",
            status="affected_component",
            explanation="Dependent consumer or test runner executing against the component.",
            evidence_ids=[eid for eid in ev_ids if "TEST" in eid],
            metadata={"project_id": project_id}
        )

        # Node 3: Failure Execution Event
        g.add_node(
            "node-failure-event",
            label="Test Suite Execution",
            component_type="failure",
            status="confirmed",
            explanation="Initial test execution failed with exit code or assertion failure.",
            evidence_ids=[eid for eid in ev_ids if "TEST" in eid],
            metadata={"project_id": project_id}
        )

        # Node 4: Repair & Verification
        g.add_node(
            "node-repair-patch",
            label="Verified Code Repair",
            component_type="commit",
            status="confirmed" if test_passed else "unverified_hypothesis",
            explanation="Targeted patch applied and verified by real test execution.",
            evidence_ids=[eid for eid in ev_ids if "PATCH" in eid],
            metadata={"verified": test_passed}
        )

        # Edges
        g.add_edge(
            "node-source-file",
            "node-test-file",
            id="edge-p1",
            label="incompatible_with",
            relationship="incompatible_with",
            animated=True
        )
        g.add_edge(
            "node-test-file",
            "node-failure-event",
            id="edge-p2",
            label="contributed_to",
            relationship="contributed_to",
            animated=True
        )
        g.add_edge(
            "node-repair-patch",
            "node-source-file",
            id="edge-p3",
            label="modified",
            relationship="modified",
            animated=False
        )

        return CausalGraphEngine._convert_networkx_to_model(g)

    @staticmethod
    def build_graph_for_scenario(
        scenario_id: str,
        root_cause_status: str = "probable",
        evidence_list: Optional[List[Dict[str, Any]]] = None
    ) -> GraphDataModel:
        g = nx.DiGraph()

        if scenario_id == "scenario-invoice-field-rename":
            g.add_node(
                "node-commit-4f8a12d",
                label="Commit 4f8a12d (Rename)",
                component_type="commit",
                status="confirmed",
                explanation="Commit 4f8a12d refactored customer API and renamed 'customer_email' to 'email'.",
                evidence_ids=["EVID-DIFF-4f8a12d", "EVID-COMMIT-4f8a12d"],
                metadata={"author": "j.doe@example.test", "file": "services/customer/api.py", "deployed": True}
            )
            g.add_node(
                "node-api-schema",
                label="Customer API Schema (/api/v1/customer)",
                component_type="api_schema",
                status="probable_cause" if root_cause_status == "probable" else "unverified_hypothesis",
                explanation="Response payload now outputs 'email' key; 'customer_email' key is no longer returned.",
                evidence_ids=["EVID-DIFF-4f8a12d", "EVID-CONTRACT-01"],
                metadata={"endpoint": "GET /api/v1/customer/{customer_id}", "missing_field": "customer_email", "new_field": "email"}
            )
            g.add_node(
                "node-workflow-step-3",
                label="Workflow Step: Extract Email",
                component_type="workflow_step",
                status="affected_component",
                explanation="Invoice workflow step 3 expects field 'customer_email' from customer response object.",
                evidence_ids=["EVID-WF-DEF", "EVID-CONTRACT-01"],
                metadata={"workflow_id": "wf-invoice-gen-v2", "step_id": "step_3", "expected_field": "customer_email"}
            )
            g.add_node(
                "node-failure-event",
                label="Invoice Execution Failure",
                component_type="failure",
                status="confirmed",
                explanation="KeyError: 'customer_email' was not found in response during invoice delivery execution.",
                evidence_ids=["EVID-FAIL-9021"],
                metadata={"failure_id": "FAIL-9021", "error_type": "SchemaFieldMissingError"}
            )

            g.add_edge("node-commit-4f8a12d", "node-api-schema", id="edge-1", label="modified", relationship="modified", animated=True)
            g.add_edge("node-api-schema", "node-workflow-step-3", id="edge-2", label="incompatible_with", relationship="incompatible_with", animated=True)
            g.add_edge("node-workflow-step-3", "node-failure-event", id="edge-3", label="contributed_to", relationship="contributed_to", animated=True)

        elif scenario_id == "scenario-ambiguous-timeout":
            g.add_node(
                "node-commit-docs",
                label="Commit 7b32c01 (Docs Update)",
                component_type="commit",
                status="confirmed",
                explanation="Recent commit updated developer README; no logic or network code was changed.",
                evidence_ids=["EVID-COMMIT-7b32c01"],
                metadata={"author": "a.kumar@example.test", "file": "README.md"}
            )
            g.add_node(
                "node-external-gateway",
                label="External Settlement Gateway",
                component_type="external_service",
                status="unverified_hypothesis",
                explanation="Third-party payment settlement gateway; failure suspected to be transient upstream timeout.",
                evidence_ids=["EVID-FAIL-8842"],
                metadata={"endpoint": "https://settlement.partner.example.test", "timeout": "30s"}
            )
            g.add_node(
                "node-workflow-reconcile",
                label="Daily Payment Reconciler",
                component_type="workflow_step",
                status="affected_component",
                explanation="Reconciliation workflow timed out while calling external gateway.",
                evidence_ids=["EVID-WF-DEF-REC"],
                metadata={"workflow_id": "wf-payment-reconcile"}
            )
            g.add_node(
                "node-failure-timeout",
                label="Gateway Timeout Error",
                component_type="failure",
                status="confirmed",
                explanation="GatewayTimeoutError after 30000ms. Root cause remains unconfirmed.",
                evidence_ids=["EVID-FAIL-8842"],
                metadata={"failure_id": "FAIL-8842"}
            )

            g.add_edge("node-commit-docs", "node-workflow-reconcile", id="edge-amb-1", label="observed_before", relationship="observed_before", animated=False)
            g.add_edge("node-external-gateway", "node-workflow-reconcile", id="edge-amb-2", label="provides", relationship="provides", animated=True)
            g.add_edge("node-workflow-reconcile", "node-failure-timeout", id="edge-amb-3", label="contributed_to", relationship="contributed_to", animated=True)

        else:
            g.add_node(
                "node-unknown-failure",
                label=f"Failure Incident ({scenario_id})",
                component_type="failure",
                status="confirmed",
                explanation="Failure event registered.",
                evidence_ids=[],
                metadata={}
            )

        return CausalGraphEngine._convert_networkx_to_model(g)

    @staticmethod
    def _convert_networkx_to_model(g: nx.DiGraph) -> GraphDataModel:
        nodes: List[GraphNodeModel] = []
        edges: List[GraphEdgeModel] = []

        x_positions = {
            "commit": 50.0,
            "api_schema": 360.0,
            "external_service": 360.0,
            "source_file": 360.0,
            "test_file": 680.0,
            "workflow_step": 680.0,
            "failure": 990.0
        }
        
        y_offsets: Dict[str, float] = {}

        for node_id, data in g.nodes(data=True):
            ctype = data.get("component_type", "workflow_step")
            base_x = x_positions.get(ctype, 400.0)
            
            cur_y_count = y_offsets.get(ctype, 0.0)
            y_offsets[ctype] = cur_y_count + 1.0
            node_y = 120.0 + (cur_y_count * 140.0)

            node_model = GraphNodeModel(
                id=node_id,
                position=GraphNodePosition(x=base_x, y=node_y),
                data=GraphNodeData(
                    label=data.get("label", node_id),
                    component_type=ctype,
                    status=data.get("status", "confirmed"),
                    explanation=data.get("explanation", ""),
                    evidence_ids=data.get("evidence_ids", []),
                    metadata=data.get("metadata", {})
                )
            )
            nodes.append(node_model)

        for u, v, data in g.edges(data=True):
            edge_model = GraphEdgeModel(
                id=data.get("id", f"{u}->{v}"),
                source=u,
                target=v,
                label=data.get("label", "related_to"),
                relationship=data.get("relationship", "observed_before"),
                animated=data.get("animated", False)
            )
            edges.append(edge_model)

        return GraphDataModel(nodes=nodes, edges=edges)
