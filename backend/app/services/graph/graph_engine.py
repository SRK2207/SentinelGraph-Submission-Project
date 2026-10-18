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
    def build_graph_for_scenario(
        scenario_id: str,
        root_cause_status: str = "probable",
        evidence_list: Optional[List[Dict[str, Any]]] = None
    ) -> GraphDataModel:
        g = nx.DiGraph()
        evidence_map = {e.get("id"): e for e in (evidence_list or [])}

        if scenario_id == "scenario-invoice-field-rename":
            # Node 1: Recent Commit
            g.add_node(
                "node-commit-4f8a12d",
                label="Commit 4f8a12d (Rename)",
                component_type="commit",
                status="confirmed",
                explanation="Commit 4f8a12d refactored customer API and renamed 'customer_email' to 'email'.",
                evidence_ids=["EVID-DIFF-4f8a12d", "EVID-COMMIT-4f8a12d"],
                metadata={
                    "author": "j.doe@example.test",
                    "file": "services/customer/api.py",
                    "deployed": True
                }
            )

            # Node 2: Backend API Schema
            g.add_node(
                "node-api-schema",
                label="Customer API Schema (/api/v1/customer)",
                component_type="api_schema",
                status="probable_cause" if root_cause_status == "probable" else "unverified_hypothesis",
                explanation="Response payload now outputs 'email' key; 'customer_email' key is no longer returned.",
                evidence_ids=["EVID-DIFF-4f8a12d", "EVID-CONTRACT-01"],
                metadata={
                    "endpoint": "GET /api/v1/customer/{customer_id}",
                    "missing_field": "customer_email",
                    "new_field": "email"
                }
            )

            # Node 3: Workflow Step 3 (Extract Email)
            g.add_node(
                "node-workflow-step-3",
                label="Workflow Step: Extract Email",
                component_type="workflow_step",
                status="affected_component",
                explanation="Invoice workflow step 3 expects field 'customer_email' from customer response object.",
                evidence_ids=["EVID-WF-DEF", "EVID-CONTRACT-01"],
                metadata={
                    "workflow_id": "wf-invoice-gen-v2",
                    "step_id": "step_3",
                    "expected_field": "customer_email"
                }
            )

            # Node 4: Workflow Execution Failure
            g.add_node(
                "node-failure-event",
                label="Invoice Execution Failure",
                component_type="failure",
                status="confirmed",
                explanation="KeyError: 'customer_email' was not found in response during invoice delivery execution.",
                evidence_ids=["EVID-FAIL-9021"],
                metadata={
                    "failure_id": "FAIL-9021",
                    "error_type": "SchemaFieldMissingError"
                }
            )

            # Directed Edges
            g.add_edge(
                "node-commit-4f8a12d",
                "node-api-schema",
                id="edge-1",
                label="modified",
                relationship="modified",
                animated=True
            )
            g.add_edge(
                "node-api-schema",
                "node-workflow-step-3",
                id="edge-2",
                label="incompatible_with",
                relationship="incompatible_with",
                animated=True
            )
            g.add_edge(
                "node-workflow-step-3",
                "node-failure-event",
                id="edge-3",
                label="contributed_to",
                relationship="contributed_to",
                animated=True
            )

        elif scenario_id == "scenario-ambiguous-timeout":
            # Ambiguous / insufficient evidence graph
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

            # Edges
            g.add_edge(
                "node-commit-docs",
                "node-workflow-reconcile",
                id="edge-amb-1",
                label="observed_before",
                relationship="observed_before",
                animated=False
            )
            g.add_edge(
                "node-external-gateway",
                "node-workflow-reconcile",
                id="edge-amb-2",
                label="provides",
                relationship="provides",
                animated=True
            )
            g.add_edge(
                "node-workflow-reconcile",
                "node-failure-timeout",
                id="edge-amb-3",
                label="contributed_to",
                relationship="contributed_to",
                animated=True
            )

        else:
            # Fallback generic graph
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

        # Calculate horizontal DAG positions
        # Nodes arranged in order: Commit (x=50) -> API / External (x=350) -> Workflow (x=650) -> Failure (x=950)
        x_positions = {
            "commit": 50.0,
            "api_schema": 360.0,
            "external_service": 360.0,
            "workflow_step": 680.0,
            "failure": 990.0
        }
        
        y_offsets: Dict[str, float] = {}

        for node_id, data in g.nodes(data=True):
            ctype = data.get("component_type", "workflow_step")
            base_x = x_positions.get(ctype, 400.0)
            
            # Stagger y if multiple of same type
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
