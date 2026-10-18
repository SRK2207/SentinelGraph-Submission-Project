# SentinelGraph Demonstration Guide — Hackloop 2026

This guide walks you through a complete 5-minute end-to-end demonstration of SentinelGraph for teammates, mentors, and hackathon judges.

---

## 1. Quick Start

### Start the Backend
In your terminal, activate the Python virtual environment and run Uvicorn:
```bash
# From workspace root
backend\venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
Verify: Open `http://localhost:8000/api/health` in your browser. You should see `"status": "healthy"`.

### Start the Frontend
In a second terminal:
```bash
cd frontend
npm.cmd run dev
```
Open `http://localhost:3000` in your browser.

---

## 2. Walkthrough Steps

### Step 1: Dashboard Overview
- **What to show**: The dark developer-tool interface, system KPIs, and the mode pill (`AI AGENT MODE` if Gemini API key is configured, or `DETERMINISTIC DEMO MODE`).
- **Talking point**: *"SentinelGraph investigates the gap between modern services: when a change happens in one service and breaks an automation workflow elsewhere, developers usually spend hours jumping across Git, APIs, and logs. SentinelGraph investigates why autonomously."*

### Step 2: Simulated Connections
- Click **Connections** in the navigation bar.
- **What to show**: The 4 simulated connectors: Git Repository, Customer Profile API, Contract Catalog, and Invoice Workflow Orchestrator.
- **Talking point**: *"SentinelGraph is built with clear boundaries. Notice the explicit 'SIMULATED / MOCK DATA' badges. We don't ask users for live OAuth credentials in this prototype; we operate against authoritative local fixtures to validate the agentic investigation model."*

### Step 3: Launching the Primary Investigation
- Click **Investigate** (or "Start Investigation" from the dashboard).
- Select **Invoice Workflow Failure — Backend Field Rename** (Primary Demo).
- Review the incident:
  - Workflow: `Invoice Customer Dispatcher` (`wf-invoice-gen-v2`)
  - Error: `KeyError: 'customer_email' was not found in customer response.`
- Click **Launch Autonomous Investigation**.

### Step 4: Live Workspace & Autonomous Tool Trace
- You will be automatically navigated to the **Live Workspace**.
- **What to show**:
  - The ordered **Investigation Trace & Tool Timeline**.
  - How the agent dynamically queried `get_failure_details`, retrieved `get_recent_commits`, inspected `get_workflow_definition`, checked `get_dependency_info`, and called `inspect_commit`.
  - Expand any event row by clicking **"Inspect Tool Payload"** to see exact JSON inputs and outputs.
  - The **Collected Evidence** sidebar with verifiable `EVID-...` IDs.
  - The **Hypotheses Evaluated** section showing supported vs refuted hypotheses.
- **Talking point**: *"SentinelGraph is a genuine tool-calling agent, not a static prompt that regurgitates pre-written text. It selects investigation tools based on what evidence is missing and validates hypotheses."*

### Step 5: Interactive Causal Graph
- Click **Causal Graph** in the navigation bar or the header button.
- **What to show**:
  - The React Flow directed graph linking:
    `Commit 4f8a12d` &rarr; `Customer API Schema` &rarr; `Workflow Step: Extract Email` &rarr; `Invoice Execution Failure`.
  - Color-coded node badges:
    - **Cyan**: Confirmed Fact
    - **Amber**: Probable Root Cause
    - **Rose**: Affected Component
  - **Click any node** (e.g. `node-commit-4f8a12d` or `node-api-schema`): The **Node Inspector** sidebar reveals the technical explanation, linked evidence IDs (`EVID-DIFF-4f8a12d`), and metadata.
- **Talking point**: *"Causation is visualized through our NetworkX engine. Every edge has a formal relationship type like 'modified', 'incompatible_with', and 'contributed_to'."*

### Step 6: Root-Cause Report & Interactive Remediation
- Click **Report & Remediation**.
- **What to show**:
  - The **Root-Cause Assessment**: High confidence, linking commit 4f8a12d in `services/customer/api.py` to the missing `customer_email` key.
  - The step-by-step **Causal Chain**.
  - Click **"Copy Report (Markdown)"** to demonstrate developer export.
  - Under **Interactive Remediation Options**, select:
    - **Option A**: `Update Workflow Field Mapping` (updates workflow step 3 to consume `email`).
  - Click **Run Simulated Verification**.
  - Notice the green verification card with details:
    `"Simulated verification passed. Workflow step 'extract_email_for_delivery' successfully consumed field 'email'."`
  - Notice the explicit transparency label:
    `"SIMULATED VERIFICATION — NO REAL WORKFLOW EXECUTED"`.

### Step 7: Uncertainty Handling (Ambiguous Scenario)
- Click **Investigate**.
- Select the second scenario: **Payment Reconciliation Timeout — Ambiguous Cause**.
- Click **Launch Autonomous Investigation**.
- View the Report:
  - Root cause status is explicitly marked **UNCONFIRMED / INSUFFICIENT EVIDENCE**.
  - SentinelGraph inspected recent commits, noted they were unrelated documentation/CSS changes, and concluded the root cause is an upstream external gateway issue.
  - The **Remaining Unknowns** section explicitly lists what is needed rather than inventing a false cause.
- **Talking point**: *"SentinelGraph doesn't hallucinate causes. When evidence is insufficient, it reports uncertainty honestly."*

### Step 8: Reset State
- Click **Reset State** in the top right navbar.
- Synthetic fixtures and in-memory caches return to their initial state.
