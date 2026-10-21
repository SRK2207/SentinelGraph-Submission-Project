# SentinelGraph

> *"A change happened here. Something broke there. SentinelGraph investigates and fixes it."*

**SentinelGraph** is an autonomous AI-powered software project failure investigation and automated code repair agent built for **Hackloop 2026**.

Modern software systems frequently suffer cross-system contract regressions — for example, when an API refactoring renames a response key from `customer_email` to `email`, silently breaking downstream billing workers and failing automation tests.

Instead of developers manually combing through error logs, test failure traces, imported dependencies, and Git histories, SentinelGraph:
1. **Safely Ingests Project Archives**: Accepts `.zip` software project uploads into dedicated, isolated filesystem sandboxes with strict path-traversal safeguards.
2. **Autonomously Discovers & Runs Real Tests**: Discovers test suites (`pytest`, `unittest`, `npm test`), executes them in sandboxed subprocesses, and observes actual exit codes and error traces.
3. **Explores Real Codebases with Dynamic Tools**: Inspects failing assertions, reads source files, searches definitions across the workspace, and identifies the root-cause defect.
4. **Applies Targeted Code Patches**: Directly modifies source files within the isolated working directory.
5. **Performs Real Verification**: Re-runs the project's real test suite to prove that all tests pass before and after the repair, generating real unified diffs and execution logs.
6. **Zero Synthetic Simulations**: Real file operations and real test runner executions. If `GEMINI_API_KEY` is not provided, the system returns an explicit error rather than fabricating fake investigation traces.

---

## Architecture & Capabilities

```
+---------------------------------------------------------------------------------+
|                                SentinelGraph UI                                 |
|  - ZIP Upload & Project Library     - Live Tool Call Execution Stream           |
|  - Interactive NetworkX Causal DAG   - Real Unified Patch Diff Viewer            |
|  - Real Test Execution Terminal Logs - One-Click Sample Defective Project Demo  |
+---------------------------------------------------------------------------------+
                                       | (REST API)
+---------------------------------------------------------------------------------+
|                                FastAPI Backend                                  |
|  - /api/projects/upload   : Path-traversal safe zip extraction                  |
|  - /api/projects/sample   : Built-in broken invoice microservice with tests     |
|  - /api/projects/run-tests: Real subprocess pytest / test runner execution      |
|  - /api/projects/diff     : difflib unified diff between original & current src |
|  - /api/investigations    : Live Gemini Agent orchestration & repair loop       |
+---------------------------------------------------------------------------------+
         |                                                 |
         v                                                 v
+-----------------------------+               +-----------------------------------+
|     Google Gemini Agent     |               |    Isolated Workspace Sandbox     |
| - list_project_files        |  <--------->  | backend/workspaces/<project_id>/  |
| - search_code               |               |   ├── original/ (pristine backup) |
| - read_file                 |               |   └── src/      (working copy)    |
| - discover_tests_and_commands|              | Safe path resolution, subprocess  |
| - run_tests (subprocess)    |               | test execution, and targeted code |
| - edit_file (real patching) |               | modification.                     |
| - get_workspace_diff        |               +-----------------------------------+
+-----------------------------+
```

---

## Technology Stack

- **Frontend**:
  - Next.js 14 (App Router)
  - React 18 & TypeScript
  - Tailwind CSS (Deep Navy/Charcoal Dark Developer Interface)
  - React Flow (`@xyflow/react`) for interactive causal DAGs
  - Lucide React icons
- **Backend**:
  - Python 3.12+
  - FastAPI & Uvicorn
  - Pydantic v2 (Strict Schema Validation)
  - Google GenAI SDK (`google-genai` 2.x)
  - NetworkX 3.x (Graph Theory & Directed DAGs)
  - Pytest & HTTPX (Automated Test Suite)
  - Python Multipart (Secure Archive Uploads)

---

## Installation & Setup

### 1. Clone & Enter Repository
```bash
cd sentinelgraph-submission
```

### 2. Backend Setup
Create a Python virtual environment and install dependencies:
```powershell
# Create virtual environment
python -m venv backend/venv

# Activate virtual environment (Windows PowerShell)
.\backend\venv\Scripts\Activate.ps1
# (Or macOS/Linux: source backend/venv/bin/activate)

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

> **Note**: A valid `GEMINI_API_KEY` is required for live AI agent investigations. If left blank, the application explicitly reports that an API key is required, preventing fabricated or simulated fallback results.

### 4. Frontend Setup
```bash
cd frontend
npm install
```

---

## Running the Application Locally

### 1. Start the FastAPI Backend
From the workspace root:
```powershell
.\backend\venv\Scripts\uvicorn.exe backend.app.main:app --host 127.0.0.1 --port 8000 --reload
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

The project includes an automated test suite with **22 passing test cases** verifying real workspace extraction, security, subprocess test execution, file editing, and agent dispatch:
```powershell
.\backend\venv\Scripts\pytest.exe backend\app\tests\test_backend.py -v
```

All 22 tests verify:
- Health, dashboard, and connection endpoints
- Safe ZIP extraction and strict rejection of path traversal attempts (`../../evil.txt`)
- Project workspace file listing, code search, and bounded file reading
- Dependency manifest discovery (`requirements.txt`, `pyproject.toml`, `package.json`)
- Subprocess test execution capturing real test failures (`KeyError: 'customer_email'`)
- Targeted file editing and real file modification in the isolated workspace
- Re-executing real tests to confirm they PASS after repair (`exit_code == 0`)
- Generating real unified diffs comparing original and patched files
- File reversion and project reset back to original uploaded snapshots
- Explicit error handling when `GEMINI_API_KEY` is missing (no simulated fallback)
- Mocked Gemini tool-calling loop verifying real project repair and test validation
- End-to-end project workflow API integration

---

## Security & Isolation Safeguards

1. **Path-Traversal Protection**: All archive extractions and filesystem tool calls (`read_file`, `write_file`, `edit_file`) validate that resolved paths strictly reside within the isolated workspace `src/` directory. Any attempt to navigate with `..` or absolute paths is rejected with `WorkspaceSecurityError`.
2. **Subprocess Isolation**: Tests run in an isolated subprocess with the working directory strictly set to the workspace's `src/` directory and `PYTHONDONTWRITEBYTECODE=1`. Command execution is protected by a strict 25-second timeout to prevent runaway processes.
3. **Preserved Original Snapshots**: Every project workspace maintains an immutable `original/` copy of the uploaded files, allowing instant rollback and verifiable unified diff generation.
4. **Credential Security**: `GEMINI_API_KEY` remains strictly on the backend. Frontend code never receives or exposes API credentials.
