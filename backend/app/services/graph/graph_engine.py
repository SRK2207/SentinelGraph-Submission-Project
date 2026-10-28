import networkx as nx
from typing import Dict, Any, List, Optional
from backend.app.schemas.investigation import (
    GraphDataModel,
    GraphNodeModel,
    GraphEdgeModel,
    GraphNodePosition,
    GraphNodeData
)
from backend.app.services.stack.stack_detector import StackDetector


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
        ev_ids = [e.get("id", "") for e in (evidence_list or [])]

        # Dynamically determine the primary source file based on project inspection
        meta = None
        try:
            meta = StackDetector.detect_workspace(project_id)
        except Exception:
            pass

        primary_file = None
        if changed_files and len(changed_files) > 0:
            primary_file = changed_files[0]
        elif evidence_list:
            for ev in evidence_list:
                f = ev.get("metadata", {}).get("file")
                if f:
                    primary_file = f
                    break

        if not primary_file and meta and meta.source_files_sample:
            # Pick first non-manifest source file
            non_manifests = [
                f for f in meta.source_files_sample
                if not any(f.endswith(m) for m in [".json", ".toml", ".txt", ".md", ".xml", ".properties"])
            ]
            primary_file = non_manifests[0] if non_manifests else meta.source_files_sample[0]

        if not primary_file:
            primary_file = "src/main"

        # Determine runner label
        is_android = meta.is_android if meta else False
        is_gradle = meta.is_gradle if meta else False
        is_node = meta.is_node if meta else False

        if is_android:
            runner_label = "Android Test Suite (JUnit / Instrumented)"
        elif is_gradle:
            runner_label = "Gradle Test Runner (JUnit)"
        elif is_node:
            runner_label = "Node.js Test Runner (Jest/npm)"
        else:
            runner_label = "Pytest Test Runner"

        # Node 1: Defective / Modified Source File
        g.add_node(
            "node-source-file",
            label=f"Source: {primary_file}",
            component_type="source_file",
            status="probable_cause",
            explanation=f"Source file '{primary_file}' evaluated during investigation.",
            evidence_ids=[eid for eid in ev_ids if "FILE" in eid or "PATCH" in eid or "SEARCH" in eid],
            metadata={"file": primary_file}
        )

        # Node 2: Dependent / Test Consumer
        g.add_node(
            "node-test-file",
            label=runner_label,
            component_type="test_file",
            status="affected_component",
            explanation=f"Target verification test suite ({runner_label}).",
            evidence_ids=[eid for eid in ev_ids if "TEST" in eid],
            metadata={"project_id": project_id}
        )

        # Node 3: Failure Execution Event
        has_prereq_missing = bool(meta and meta.missing_prerequisites)
        fail_label = "Prerequisite Limitation" if has_prereq_missing else "Test Suite Execution"
        fail_expl = (
            f"Missing prerequisites on host: {'; '.join(meta.missing_prerequisites)}"
            if has_prereq_missing else
            ("Tests passed successfully." if test_passed else "Test execution failed with assertion/error trace.")
        )
        g.add_node(
            "node-failure-event",
            label=fail_label,
            component_type="failure",
            status="confirmed",
            explanation=fail_expl,
            evidence_ids=[eid for eid in ev_ids if "TEST" in eid],
            metadata={"project_id": project_id, "has_prereq_missing": has_prereq_missing}
        )

        # Node 4: Repair & Verification
        repair_status = "confirmed" if test_passed else "unverified_hypothesis"
        repair_label = "Verified Code Repair" if test_passed else ("Prerequisite Assessment" if has_prereq_missing else "Unverified Patch")
        g.add_node(
            "node-repair-patch",
            label=repair_label,
            component_type="commit",
            status=repair_status,
            explanation="Targeted patch applied and verified by real tests." if test_passed else "Investigation findings awaiting live environment verification.",
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

        # If missing host prerequisites, add an external prerequisite node
        if has_prereq_missing:
            g.add_node(
                "node-prereq-env",
                label="Host Build Tools",
                component_type="external_service",
                status="unverified_hypothesis",
                explanation=f"Host machine requires: {', '.join(meta.missing_prerequisites)}",
                evidence_ids=[],
                metadata={"missing": meta.missing_prerequisites}
            )
            g.add_edge(
                "node-prereq-env",
                "node-failure-event",
                id="edge-p4",
                label="blocks",
                relationship="incompatible_with",
                animated=True
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
