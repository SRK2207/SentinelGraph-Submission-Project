# SentinelGraph

> *"A change happened here. Something broke there. SentinelGraph investigates why."*

**SentinelGraph** is an agentic AI-powered cross-system workflow failure investigation and root-cause analysis platform built for **Hackloop 2026**.

When a change in one system (such as an API response field rename or a database schema alteration) silently breaks a dependent automation workflow elsewhere, developers typically spend hours inspecting disparate Git logs, API responses, dependency relationships, and workflow configurations.

SentinelGraph solves this problem by autonomously investigating the failure, collecting verifiable evidence across systems, evaluating competing hypotheses, constructing a directed causal graph, generating actionable remediations, and running simulated verifications.

---

## Key Features

1. **Autonomous Tool Selection**: Leverages native Gemini function calling. The agent inspects incident failure details, decides what information is missing, dynamically executes registered investigation tools, and observes returned evidence.
2. **Strict Evidence Provenance**: Every claim, hypothesis, causal edge, and remediation is linked to verifiable evidence IDs (`EVID-...`) captured from synthetic repository diffs, contracts, and workflow definitions.
3. **Interactive Causal Dependency Graph**: Built with **NetworkX** on the backend and rendered with **React Flow** on the frontend. Visually distinguishes confirmed facts, probable causes, affected components, and unverified hypotheses.
4. **Honest Uncertainty Handling**: When evidence is insufficient (e.g. external network timeouts unrelated to repository commits), SentinelGraph reports root causes as unconfirmed and identifies remaining unknowns rather than hallucinating causes.
5. **Interactive Remediation & Simulated Verification**: Select proposed remediations and execute simulated verifications against controlled synthetic state.
6. **Two Distinct Operating Modes**:
   - **AI AGENT MODE**: Uses live Gemini API tool calling with your Google AI Studio API key.
   - **DETERMINISTIC DEMO MODE**: Works 100% offline without requiring an API key, executing the identical investigation trace for seamless demonstration.

---

## Technology Stack

- **Frontend**:
  - Next.js 14 (App Router)
  - React 18 & TypeScript
  - Tailwind CSS (Deep Navy/Charcoal Dark Developer-Tool Interface)
  - React Flow (`@xyflow/react`) for interactive causal graphs
  - Lucide React icons
- **Backend**:
  - Python 3.12+
  - FastAPI & Uvicorn
  - Pydantic v2 (Validation & Schemas)
  - Google GenAI SDK (`google-genai` 2.x)
  - NetworkX 3.x (Graph Theory & Directed DAGs)
  - Pytest & HTTPX (Automated Test Suite)
- **Data**:
  - Local synthetic JSON fixtures representing multi-system states

---

## Prerequisites

- **Python**: 3.10+ (Tested on Python 3.12)
- **Node.js**: v18+ (Tested on Node v24)
- **npm**: 9+
- **Google AI Studio API Key** *(Optional)*: Required for live Gemini Agent Mode; if omitted, the application runs in Deterministic Demo Mode.

---

## Installation & Setup

### 1. Repository Directory
```bash
cd sentinelgraph-submission
```

### 2. Backend Setup
Create a Python virtual environment and install dependencies:
```bash
# Create virtual environment
python -m venv backend/venv

# Activate virtual environment (Windows PowerShell)
.\backend\venv\Scripts\Activate.ps1
# (Or on macOS/Linux: source backend/venv/bin/activate)

# Install dependencies
pip install -r backend/requirements.txt
```

### 3. Configure Environment Variables
Copy the example environment file:
```bash
cp backend/.env.example backend/.env
```
Edit `backend/.env`:
```env
# Optional: Add your Google AI Studio Gemini API key
GEMINI_API_KEY=your_gemini_api_key_here

# Configurable Gemini Model
GEMINI_MODEL=gemini-2.5-flash

# Frontend Origin for CORS
FRONTEND_ORIGIN=http://localhost:3000

# Safety Guardrails
MAX_AGENT_ITERATIONS=8
MAX_TOOL_CALLS=12
```

> **Note**: If `GEMINI_API_KEY` is left blank, SentinelGraph runs in **DETERMINISTIC DEMO MODE**.

### 4. Frontend Setup
```bash
cd frontend
npm install
```

---

## Running the Application Locally

### 1. Start the FastAPI Backend
From the workspace root:
```bash
backend\venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
```
The backend starts at `http://127.0.0.1:8000`. You can inspect the interactive OpenAPI documentation at `http://127.0.0.1:8000/docs`.

### 2. Start the Next.js Frontend
In a separate terminal:
```bash
cd frontend
npm run dev
```
Open your browser at `http://localhost:3000`.

---

## Running Automated Backend Tests

The project includes an automated test suite covering 25 comprehensive backend test cases:
```bash
backend\venv\Scripts\pytest.exe backend\app\tests\test_backend.py -v
```

All 25 tests verify:
- Health and scenario endpoints
- All 5 investigation tools (`get_failure_details`, `get_recent_commits`, `get_workflow_definition`, `get_dependency_info`, `inspect_commit`)
- Tool argument aliasing (e.g., `commit_hash`, `sha`, `count`)
- Argument and payload validation
- Agent iteration and tool-call safety limits
- Missing API key & Gemini error fallbacks
- Evidence provenance integrity & zero-evidence degradation
- Uncertainty handling & confidence reduction when code diffs are unobserved
- NetworkX graph construction and edge validation
- Simulated successful and unsuccessful remediations
- Verifier edge cases and error handling
- End-to-end investigation API lifecycle
- Demo reset behavior

---

## Demonstration Scenarios

1. **Invoice Workflow Failure — Backend Field Rename (Primary Demo)**
   - **Context**: A developer refactored the customer profile API response in commit `4f8a12d`, renaming field `customer_email` to `email`.
   - **Failure**: The invoice automation workflow (`wf-invoice-gen-v2`) failed with `KeyError: 'customer_email'`.
   - **Investigation**: SentinelGraph autonomously queries failure details, discovers recent commits, inspects the git diff, checks workflow definitions, builds a causal chain, and recommends updating the workflow field mapping or adding a backward-compatible alias.
   - **Verification**: Selecting a remediation simulates the fix and verifies resolution.

2. **Payment Reconciliation Timeout — Ambiguous Cause (Uncertainty Test)**
   - **Context**: Daily payment reconciliation failed due to an external gateway timeout after 30s.
   - **Investigation**: Recent code commits only touched documentation and CSS.
   - **Result**: SentinelGraph explicitly reports the root cause as **UNCONFIRMED / INSUFFICIENT EVIDENCE** and lists remaining unknowns rather than hallucinating an internal code cause.

---

## Documentation

- [Architecture Guide](docs/ARCHITECTURE.md): System design, agent tool-calling loop, NetworkX graph engine, and evidence provenance model.
- [API Reference](docs/API.md): Full documentation of all REST endpoints, request/response models, and error behaviors.
- [Demonstration Guide](docs/DEMO_GUIDE.md): 5-minute step-by-step walkthrough script for teammates, mentors, and hackathon judges.

---

## Security & Transparency Notes

- **API Key Security**: The Gemini API key remains strictly on the backend and is never exposed to the browser or returned in API responses.
- **Controlled Execution**: The AI agent cannot execute arbitrary shell commands, access arbitrary local disk paths, or modify external code.
- **Simulated Verification Notice**: All verification actions operate purely on synthetic in-memory fixtures and carry the label:
  `"SIMULATED VERIFICATION — NO REAL WORKFLOW EXECUTED"`.
- **Honest Mode Signaling**: The application visibly displays whether it is running in `AI AGENT MODE` or `DETERMINISTIC DEMO MODE`. Fallback runs are never misrepresented.
