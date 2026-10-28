# SentinelGraph

> *"A change happened here. Something broke there. SentinelGraph investigates and fixes it."*

**SentinelGraph** is an autonomous AI-powered software project failure investigation and automated code repair agent built for **Hackloop 2026**.

Modern software systems frequently suffer cross-system contract regressions — for example, when an API refactoring renames a response key from `customer_email` to `email`, silently breaking downstream billing workers and failing automation tests.

Instead of developers manually combing through error logs, test failure traces, imported dependencies, and Git histories, SentinelGraph:
1. **Safely Ingests Project Archives**: Accepts `.zip` software project uploads into dedicated, isolated filesystem sandboxes with strict path-traversal safeguards.
2. **Autonomously Discovers & Runs Real Tests**: Discovers test suites (`pytest`, `unittest`, `npm test`), executes them in sandboxed subprocesses with zero-leak environment scrubbing, and observes actual exit codes and error traces.
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
|  - /api/health            : Security isolation boundary & environment profile   |
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
git clone https://github.com/SRK2207/SentinelGraph-Submission-Project.git
cd SentinelGraph-Submission-Project
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

# Configurable Gemini Model (e.g. gemini-flash-lite-latest, gemini-flash-latest)
GEMINI_MODEL=gemini-flash-lite-latest

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
From the repository root:
```powershell
.\backend\venv\Scripts\python.exe -m uvicorn backend.app.main:app --host 127.0.0.1 --port 8000
```
The backend starts at `http://127.0.0.1:8000`. You can inspect the interactive OpenAPI documentation at `http://127.0.0.1:8000/docs`.

### 2. Start the Next.js Frontend
In a separate terminal:
```bash
cd frontend
npm run start
```
*(Or `npm run dev` for development mode).* Open your browser at `http://localhost:3000`.

---

## Running Automated Backend Tests

The project includes an automated test suite with **35 passing test cases** across backend integration, general-purpose multi-stack routing, and security isolation:
```powershell
.\backend\venv\Scripts\pytest.exe backend\app\tests -v
```

All 35 tests verify:
- **Core Backend Suite (22 tests)**:
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
  - End-to-end project workflow API integration
- **General-Purpose Multi-Stack Adapters (7 tests)**:
  - Stack detection for Python, Node.js/TypeScript, and Gradle/Android
  - Adapter routing (ensuring Gradle/Android never misroutes to pytest)
  - Missing build toolchain prerequisite handling with honest reporting
  - Causal graph file-anchoring without phantom fallbacks
- **Security & Isolation Boundary (6 tests)**:
  - Zero-leak environment sanitization: Proves `GEMINI_API_KEY` and host credentials are strictly scrubbed from subprocess environments
  - Output stream buffer capping (512KB cap) preventing memory exhaustion DoS
  - Reliable process-tree termination on timeout using `taskkill /F /T`
  - Workspace directory traversal rejection
  - Snapshot immutability ensuring `original/` is never modified during agent investigation
  - Host execution security profile capability reporting (`HOST_PROCESS_RESTRICTED`)

---

## Security & Isolation Safeguards

1. **Zero-Leak Environment Scrubbing**: Tests run with an explicitly whitelisted set of system variables (`SYSTEMROOT`, `PATH`, etc.). All variables matching `(KEY|SECRET|TOKEN|CREDENTIAL|PASSWORD|AUTH|GEMINI|API|AWS|AZURE|GCP)` are purged before subprocess launch.
2. **Output Stream Bounding**: Stdout and stderr streams are capped at 512KB to prevent memory exhaustion DoS from infinite loop print statements.
3. **Process-Tree Termination**: Command execution is bounded by timeouts, reliably terminating the entire process hierarchy on Windows/POSIX.
4. **Path-Traversal Protection**: All archive extractions and filesystem tool calls (`read_file`, `write_file`, `edit_file`) validate that resolved paths strictly reside within the workspace `src/` directory.
5. **Preserved Original Snapshots**: Every project workspace maintains an immutable `original/` copy of the uploaded files, allowing instant rollback and verifiable unified diff generation.
6. **Transparent Capability Disclaimers**: In environments without Docker or WSL, SentinelGraph runs in `HOST_PROCESS_RESTRICTED` mode and explicitly reports this limitation in `/api/health` and investigation records rather than making unverified containerization claims.

---

## Detailed Empirical Validation & Security Reports

For in-depth analysis, telemetry, Mermaid diagrams, and empirical results across multiple stacks and complex defect scenarios, refer to the documentation in `docs/`:
- [**Security & Advanced Autonomous Repair Evaluation Report**](docs/SECURITY_AND_ADVANCED_VALIDATION_REPORT.md): In-depth report covering the 6 advanced defect fixtures (coordinated multi-file defects, configuration dependency alignment, red herrings, regression guards, and unresolvable contradictory specifications) executed against live models.
- [**Empirical Validation Report**](docs/EMPIRICAL_VALIDATION_REPORT.md): Initial multi-stack autonomous repair validation covering Python, Node.js, and Kotlin/Gradle.
- [**Architecture Guide**](docs/ARCHITECTURE.md): Architectural deep-dive into the agent loop and graph engine.
