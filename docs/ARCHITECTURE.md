# SentinelGraph Architecture Documentation

## 1. System Overview

SentinelGraph is an agentic AI-powered cross-system workflow failure investigation and root-cause analysis platform. When a change in one system (e.g., an API response field rename in a backend service) breaks a dependent component elsewhere (e.g., an automated invoice workflow expecting the legacy field name), SentinelGraph autonomously investigates the failure, collects verifiable evidence across systems, evaluates competing hypotheses, constructs a causal dependency graph, generates an actionable remediation, and provides simulated verification.

```
+-------------------------------------------------------------+
|                      SentinelGraph UI                       |
|  (Next.js 14, React Flow, Lucide, Tailwind CSS - Dark Theme)|
+------------------------------+------------------------------+
                               | REST API (HTTP/JSON)
+------------------------------v------------------------------+
|                   FastAPI Backend Core                      |
|  - API Router (/api/scenarios, /api/investigations, etc.)   |
|  - In-Memory Investigation & Scenario Store                 |
|  - CORS & Security Boundary Protection                      |
+------------------------------+------------------------------+
                               |
       +-----------------------+-----------------------+
       |                                               |
+------v-----------------------+     +-----------------v------+
|    Agent Orchestrator        |     |  Causal Graph Engine   |
|  - Google GenAI SDK (Gemini) |     |  - NetworkX Processing |
|  - Dynamic Tool Selection    |     |  - Node & Edge Schemas |
|  - Iterative Reasoning Loop  |     |  - Provenance Mapping  |
|  - Deterministic Fallback    |     +------------------------+
+--------------+---------------+
               | Invokes Registered Tools
+--------------v-----------------------------------------------+
|                 Controlled Investigation Tools               |
|  - get_failure_details     - get_recent_commits              |
|  - get_dependency_info     - get_workflow_definition         |
|  - inspect_commit                                            |
+------------------------------+-------------------------------+
                               | Queries Data Fixtures
+------------------------------v-------------------------------+
|               Authoritative Synthetic Fixtures               |
|  - Invoice Field Rename Scenario (Primary)                   |
|  - Ambiguous Timeout Scenario (Uncertainty Handling)         |
+--------------------------------------------------------------+
```

---

## 2. Frontend & Backend Responsibilities

### Frontend Responsibilities
- **Render Clean Developer UI**: Dark developer-tool interface with navy/charcoal styling, subtle borders, high-contrast badges, and clear hierarchy.
- **Interactive Visualizations**: Interactive React Flow diagram for the causal graph with pan/zoom, fit-to-view, node selection, and detailed node inspections.
- **Workflow State Management**: Real-time polling and status display during investigation runs, showing timeline events, observed evidence, and candidate causes.
- **Remediation & Verification UX**: Enable users to select simulated remediations and trigger verified checks with explicit labeling.
- **Security Boundary**: The frontend **never** interacts directly with the Gemini API; it communicates exclusively with the FastAPI backend.

### Backend Responsibilities
- **API & State Management**: Maintain scenario states, active investigations, and event traces.
- **Agent Orchestration**: Initialize Gemini client, register Python tools, execute the iterative function-calling loop, enforce iteration limits (`MAX_AGENT_ITERATIONS`, `MAX_TOOL_CALLS`), and capture trace events.
- **Deterministic Fallback**: Seamlessly provide a deterministic demonstration mode when Gemini credentials are absent or when rate limits occur, clearly signaling `DETERMINISTIC DEMO MODE`.
- **Causal Graph Engine**: Process observed findings into a NetworkX directed graph, validating dependencies, relationships, and evidence mappings.
- **Synthetic Fixtures**: Provide deterministic, repeatable demonstration data across systems without requiring external cloud accounts or credentials.

---

## 3. Agent Tool-Calling Lifecycle

The agent loop leverages Gemini's native tool-calling capabilities with safe backend execution:

```
[START INVESTIGATION]
         |
         v
[Initialize Investigation Context & Prompt]
         |
         v
[Submit Context + Tool Declarations to Gemini]
         |
         +<----------------------------------------------------+
         |                                                     |
         v                                                     |
[Gemini Evaluates State & Generates Tool Call]                 |
         |                                                     |
         v                                                     |
[Backend Validates Tool Name & Arguments]                      |
         |                                                     |
         +--> Is tool registered and allowed?                  |
         |         | Yes                                       |
         |         v                                           |
         |    [Execute Python Tool Function]                   |
         |         |                                           |
         |         v                                           |
         |    [Record Evidence & Event Trace]                  |
         |         |                                           |
         |         v                                           |
         |    [Format Tool Response & Return to Gemini]        |
         |         |                                           |
         |         +-------------------------------------------+
         |
         +--> Does Gemini conclude investigation (Finish / Max Limit)?
                   | Yes
                   v
       [Generate Structured Report]
                   |
                   v
       [Construct NetworkX Causal Graph]
                   |
                   v
       [Investigation Complete]
```

### Safety & Guardrails
- **No Arbitrary Execution**: Gemini cannot execute arbitrary bash/shell commands, run unapproved Python code, or access local files outside the registered tools.
- **Iteration Limits**: Execution halts if agent exceeds `MAX_AGENT_ITERATIONS` or `MAX_TOOL_CALLS` to prevent infinite loops.
- **Model Output Validation**: Model output is parsed into strict Pydantic models; unvalidated fields or hallucinated references are rejected or marked unconfirmed.

---

## 4. Evidence Model & Provenance

Evidence is the fundamental unit of truth in SentinelGraph. Hypotheses must not be treated as facts unless backed by observed evidence.

### Evidence Structure
```json
{
  "id": "EVID-001",
  "type": "commit_diff",
  "title": "Customer response field renamed",
  "description": "Commit 4f8a12d changed response field 'customer_email' to 'email'.",
  "source": "mock_repository",
  "timestamp": "2026-10-11T09:14:22Z",
  "relevance": "high",
  "observed": true,
  "metadata": {
    "commit_id": "4f8a12d",
    "file": "services/customer/api.py"
  }
}
```

Every claim, hypothesis, causal graph edge, and remediation recommendation links back to one or more evidence IDs (`evidence_ids`). If evidence is insufficient, SentinelGraph explicitly sets status to `unconfirmed` and reports `remaining_unknowns`.

---

## 5. Causal Graph Engine

The backend causal graph is built using **NetworkX** (`DiGraph`):

### Node Types & Visual States
1. `commit`: Code or configuration change (e.g., Commit `4f8a12d`).
2. `api_schema`: API contract or schema definition (e.g., `/api/v1/customer`).
3. `workflow_step`: Automation step or dependency (e.g., Invoice Email Extraction Step).
4. `failure`: The resulting failure event (e.g., Workflow Execution Error).

### Edge Relationships
- `modified`: Commit modified API schema (`commit -> api_schema`).
- `provides`: Backend API provides data contract.
- `consumes`: Workflow consumes API contract.
- `incompatible_with`: Schema change introduced incompatibility with workflow expectation.
- `contributed_to`: Incompatibility contributed to workflow failure.

The graph is translated to frontend-ready React Flow nodes (`id`, `position`, `data`, `type`) and edges (`id`, `source`, `target`, `label`, `animated`, `style`).

---

## 6. Verification Boundaries & Safety

- **Controlled Synthetic State**: Verification operates purely against synthetic fixtures in backend memory.
- **Explicit Labeling**: Every verification output displays:
  `"SIMULATED VERIFICATION — NO REAL WORKFLOW EXECUTED"`
- **Strict Read-Only Agent**: The AI agent is strictly an investigative assistant; it cannot modify live production code or trigger real external deployments.
