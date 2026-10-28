# SentinelGraph: Empirical Validation of Autonomous Software Repair

**Date:** 2026-10-28  
**Live Configured Model:** `gemini-flash-lite-latest` (Google GenAI Interactions SDK)  
**Evaluation Target:** `sentinelgraph-submission`  
**Untouched Baseline:** `SentinelGraph-MVP` (strictly preserved at tag `mvp-baseline-2026-10-18`)  

---

## 1. Test Suite Architecture: Mocked vs. Real Model Integration

An inspection of the test infrastructure reveals a clear division between automated CI unit tests and live agent execution:

| Test File | Test Count | Mocked vs. Real Model | Purpose & Scope |
| :--- | :---: | :--- | :--- |
| [`backend/app/tests/test_backend.py`](file:///c:/Users/LENOVO/OneDrive/Documents/UNIVERSITY/Second_Year_(2026-27)/Projects/sentinelgraph-submission/backend/app/tests/test_backend.py) | 22 | **Mocked / Unit** | Validates workspace management, path traversal security, API endpoints, tool execution, diff generation, and mocked 4-turn tool-calling loops (`patch("genai.Client")`). **Does not make live network API calls.** |
| [`backend/app/tests/test_general_purpose.py`](file:///c:/Users/LENOVO/OneDrive/Documents/UNIVERSITY/Second_Year_(2026-27)/Projects/sentinelgraph-submission/backend/app/tests/test_general_purpose.py) | 7 | **Deterministic / Unit** | Validates manifest detection across Python, Node, and Android/Gradle, verifies adapter dispatching (preventing Gradle from misrouting to pytest), and verifies causal graph integrity. **Zero mock responses; tests deterministic stack logic.** |
| **Live Empirical Validation Harness** | 3 | **Live Real Model** (`gemini-flash-lite-latest`) | Drives full end-to-end autonomous investigation, tool calling, source code patching on disk, subprocess verification execution, and causal graph synthesis against three independent fixtures. |

**Key Finding:** Automated test suites (`pytest`) pass 29/29 tests, but rely on mocked tool loops to avoid consuming external API quota, flakiness, or network dependency. **Mocked test passes do not prove autonomous repair.** True autonomous repair was therefore independently evaluated against three real, isolated project fixtures using the live Gemini model.

---

## 2. Empirical Validation Results Across Controlled Fixtures

Three independent, reproducible project fixtures were created in isolated workspaces and subjected to the complete SentinelGraph pipeline.

```mermaid
flowchart TD
    subgraph Fixture 1: Python
        A1["fixture_python_calc.zip"] --> B1["StackDetector: Python / pytest"]
        B1 --> C1["Initial Diagnostics: 2 Failed, 1 Passed (Exit 1)"]
        C1 --> D1["Live Gemini Agent (gemini-flash-lite-latest)"]
        D1 --> E1["Patch Applied to calc.py"]
        E1 --> F1["Verification: 3 Passed in 0.04s (Exit 0)"]
        F1 --> G1["Verdict: PASS"]
    end

    subgraph Fixture 2: Node.js
        A2["fixture_node_slugify.zip"] --> B2["StackDetector: JS / npm test"]
        B2 --> C2["Initial Diagnostics: AssertionError (Exit 1)"]
        C2 --> D2["Live Gemini Agent (gemini-flash-lite-latest)"]
        D2 --> E2["Patch Applied to slugify.js"]
        E2 --> F2["Verification: All tests passed (Exit 0)"]
        F2 --> G2["Verdict: PASS"]
    end

    subgraph Fixture 3: Kotlin / Android
        A3["fixture_kotlin_attendance.zip"] --> B3["StackDetector: Kotlin / Gradle / Android"]
        B3 --> C3["Initial Diagnostics: Prerequisite Limitation"]
        C3 --> D3["GradleKotlinAdapter blocks Pytest misrouting"]
        D3 --> E3["Status: UNRESOLVED / Verification: NOT_RUN"]
        E3 --> G3["Verdict: BLOCKED"]
    end
```

---

### Fixture 1: Python (`fixture_python_calc`)
* **Verdict:** `PASS` (Genuine Autonomous Code Repair Verified)

| Dimension | Details |
| :--- | :--- |
| **Project ID** | `proj-78eca595a2` |
| **Detected Stack** | Primary Language: `python`, Build: `pip`, Framework: `pytest`, Suggested Command: `pytest` |
| **Original Defect** | In `calc.py`, `calculate_discounted_price()` computed `return price + discount` instead of subtracting the discount. |
| **Initial Verification** | **FAILED** (`pytest`). Exit code: `1`. Output: `FAILED test_calc.py::test_twenty_percent_discount - AssertionError: Expected 80.0 but got 120.0` (2 failed, 1 passed in 0.37s). |
| **Agent Reasoning & Tools** | Model: `gemini-flash-lite-latest`. Elapsed Time: **45.09s**. Total timeline events: 20. Tool sequence: `list_project_files` -> duplicate suppressed by loop guard -> `read_file(test_calc.py)` -> `read_file(calc.py)` -> `run_tests` (confirmed failure) -> `edit_file(calc.py)` -> `run_tests` (verified) -> `get_workspace_diff`. |
| **Actual Patch Applied** | ```diff
--- a/calc.py
+++ b/calc.py
@@ -2,4 +2,4 @@
     """Calculates the price after applying a percentage discount."""
     discount = price * (discount_percent / 100.0)
     # DEFECT: Adds discount instead of subtracting it!
-    return price + discount
+    return price - discount
``` |
| **Post-Patch Verification** | **PASSED** (`pytest`). Exit code: `0`. Duration: 0.04s. `============================== 3 passed in 0.04s ==============================`. |
| **Final Investigation Status** | `status: "completed"`, `verification.status: "passed"`, `verification.simulated: False`. |
| **Causal Graph Integrity** | 4 nodes, 3 edges. Nodes: `Source: calc.py`, `Pytest Test Runner`, `Test Suite Execution`, `Verified Code Repair`. Zero phantom `customer_service.py` nodes. |
| **Telemetry Artifact** | [`scratch/results_python_calc.json`](file:///C:/Users/LENOVO/.gemini/antigravity/brain/3a77f8c8-2efd-40a5-93fa-c0aee7c49897/scratch/results_python_calc.json) |

---

### Fixture 2: Node.js / JavaScript (`fixture_node_slugify`)
* **Verdict:** `PASS` (Genuine Autonomous Code Repair Verified)

| Dimension | Details |
| :--- | :--- |
| **Project ID** | `proj-c35858f2e8` |
| **Detected Stack** | Primary Language: `javascript`, Build: `npm`, Framework: `npm-test`, Suggested Command: `npm test` |
| **Original Defect** | In `slugify.js`, `slugify()` only called `.toLowerCase().trim()`, failing to replace whitespace characters with hyphens. |
| **Initial Verification** | **FAILED** (`npm test` -> `node test.js`). Exit code: `1`. Output: `AssertionError [ERR_ASSERTION]: Should convert single space to hyphen. actual: 'hello world', expected: 'hello-world'`. |
| **Agent Reasoning & Tools** | Model: `gemini-flash-lite-latest`. Elapsed Time: **42.15s**. Total timeline events: 17. Tool sequence: `list_project_files` -> `read_file(test.js)` -> `read_file(slugify.js)` -> `edit_file(slugify.js)` -> `run_tests(npm test)` -> `get_workspace_diff`. |
| **Actual Patch Applied** | ```diff
--- a/slugify.js
+++ b/slugify.js
@@ -1,7 +1,6 @@
 function slugify(text) {
     if (!text) return "";
-    // DEFECT: Forgets to replace spaces with hyphens, only converts to lowercase!
-    return text.toLowerCase().trim();
+    return text.toLowerCase().trim().replace(/\s+/g, "-");
 }
 
 module.exports = { slugify };
``` |
| **Post-Patch Verification** | **PASSED** (`npm test`). Exit code: `0`. Output: `All slugify tests passed successfully!`. |
| **Final Investigation Status** | `status: "completed"`, `verification.status: "passed"`, `verification.simulated: False`. |
| **Causal Graph Integrity** | 4 nodes, 3 edges. Nodes: `Source: slugify.js`, `Node.js Test Runner (Jest/npm)`, `Test Suite Execution`, `Verified Code Repair`. Zero phantom `customer_service.py` nodes. |
| **Telemetry Artifact** | [`scratch/results_node_slugify.json`](file:///C:/Users/LENOVO/.gemini/antigravity/brain/3a77f8c8-2efd-40a5-93fa-c0aee7c49897/scratch/results_node_slugify.json) |

---

### Fixture 3: Kotlin / Gradle / Android (`fixture_kotlin_attendance`)
* **Verdict:** `BLOCKED` (Clean, Honest Prerequisite Limitation Handling)

| Dimension | Details |
| :--- | :--- |
| **Project ID** | `proj-eb4153e6a6` |
| **Detected Stack** | Primary Language: `kotlin`, `is_android: True`, `is_gradle: True`, Build: `gradle`, Frameworks: `android-junit`, `gradle-test`. Missing Prerequisites: `Gradle build tool / wrapper not found`, `Android SDK (ANDROID_HOME/ANDROID_SDK_ROOT) not configured on host`. |
| **Original Defect** | In `AttendanceService.kt`, `calculateAttendanceRate()` multiplied ratio by `10.0` instead of `100.0`. |
| **Initial Verification** | **PREREQUISITE MISSING**. Status: `prerequisite_missing`. Passed: `False`. Exit code: `None`. Explicit message: `ENVIRONMENT PREREQUISITE LIMITATION: SentinelGraph strictly refuses to run unrelated test runners (such as pytest) or fabricate results.` |
| **Adapter Non-Misrouting** | Verified: `GradleKotlinAdapter` was dispatched. Pytest was **never called**. |
| **Agent Behavior** | Explored workspace files via `list_project_files`, read `AttendanceService.kt` and `AttendanceServiceTest.kt`, proposed static patch to `AttendanceService.kt`. |
| **Verification & Honesty Check** | Because the Gradle/Android SDK prerequisite was missing on the host, SentinelGraph **refused to claim a verified repair**. Verification status remained `not_run`, and overall status was marked as `unresolved`. |
| **Final Investigation Status** | `status: "unresolved"`, `verification.status: "not_run"`, `verification.simulated: False`. |
| **Causal Graph Integrity** | 5 nodes, 4 edges. Nodes: `Source: app/.../AttendanceService.kt`, `Android Test Suite (JUnit / Instrumented)`, `Prerequisite Limitation`, `Prerequisite Assessment`, `Host Build Tools`. Zero phantom `customer_service.py` nodes. |
| **Telemetry Artifact** | [`scratch/results_kotlin_attendance.json`](file:///C:/Users/LENOVO/.gemini/antigravity/brain/3a77f8c8-2efd-40a5-93fa-c0aee7c49897/scratch/results_kotlin_attendance.json) |

---

## 3. Comparative Telemetry & Quota Summary

| Metric | Python Fixture (`calc`) | Node.js Fixture (`slugify`) | Kotlin/Android Fixture (`attendance`) |
| :--- | :---: | :---: | :---: |
| **Model Used** | `gemini-flash-lite-latest` | `gemini-flash-lite-latest` | `gemini-flash-lite-latest` |
| **Investigation ID** | `INV-VAL-PYTHON-1793165412` | `INV-VAL-NODE-1793165484` | `INV-VAL-KOTLIN-1793165674` |
| **Elapsed Wall Time** | **45.09s** | **42.15s** | **23.76s** |
| **API Reasoning Turns** | 5 turns | 4 turns | 3 turns |
| **Tool Calls Executed** | 7 calls | 5 calls | 4 calls |
| **Duplicate Calls Suppressed** | 1 (`list_project_files`) | 0 | 0 |
| **Rate Limit / 429 Errors** | 0 | 0 | 0 |
| **Server 500/503 Errors** | 0 | 0 | 0 |
| **Disk Patch Verified?** | **YES** (`calc.py`) | **YES** (`slugify.js`) | Static edit only (`AttendanceService.kt`) |
| **Post-Repair Test Exit Code** | `0` (3 passed) | `0` (all passed) | `None` (Prerequisite Missing) |
| **Final Investigation State** | `completed` | `completed` | `unresolved` |
| **Verification Verdict** | **PASS** | **PASS** | **BLOCKED** |

---

## 4. Execution-Isolation & Security Guarantees

An audit of the implementation establishes the following concrete boundaries:

### Proven Security Guarantees
1. **Strict Path Containment:**
   - In `WorkspaceManager.resolve_safe_path`, every file operation is strictly resolved and checked with `target.relative_to(src_dir)`. Attempts to escape via `../` or absolute paths raise `WorkspaceSecurityError` and return HTTP 400.
2. **Zip-Bomb & Extraction Defenses:**
   - Extraction enforces hard quotas: max 25MB archive size, max 100MB uncompressed size, and max 1,000 files. Null bytes and absolute tar/zip entries are rejected before writing to disk.
3. **Workspace Isolation & Reset Guarantees:**
   - Workspaces are split into `src/` and `original/`. Mutations never touch `original/` or the host codebase. Calling `reset_project` completely wipes `src/` and restores from `original/`.
4. **Execution Bounding:**
   - Every subprocess call is wrapped with `timeout=25` seconds. Iteration caps (`MAX_AGENT_ITERATIONS=8`, `MAX_TOOL_CALLS=12`) prevent infinite execution or runaway API consumption.
5. **Anti-Hallucination & Simulation Prohibition:**
   - If a test cannot run due to missing host tools, the system explicitly marks `verification.status = "not_run"` and `report.status = "unresolved"`. It strictly prohibits marking simulated hypotheses as verified repairs.

### Unproven / Environmental Limitations
1. **Host Subprocess Privilege Isolation:**
   - In the local Windows environment, `subprocess.run` executes under the current OS user token. If an untrusted project contained malicious build scripts (e.g. `npm test` invoking arbitrary shell binaries), it would execute with host user privileges. Full untrusted code isolation requires OS-level containerization (e.g., Docker containers with dropped capabilities, read-only root, and seccomp profiles).
2. **Host Compiler / SDK Availability:**
   - SentinelGraph cannot autonomously compile Kotlin/Android or native code if the host lacks the necessary toolchains (Android SDK, Java JDK, Gradle). It correctly refuses to fake verification, but cannot repair such defects dynamically without external environment provisioning.

---

## 5. Final Assessment: Demonstrated vs. Unproven Capabilities

### Demonstrated Capabilities
* **Genuine Autonomous Repair on Python:** Indicated by real model reading files, pinpointing defects, editing code, re-running pytest, and producing real exit code 0.
* **Genuine Autonomous Repair on Node.js/JavaScript:** Indicated by real model inspecting `package.json` and `test.js`, patching regex replacement in `slugify.js`, and verifying via `npm test` (exit code 0).
* **Multi-Ecosystem Detection:** Reliably classifies Python, Node.js, and Android/Gradle manifests.
* **Cross-Runner Contamination Immunity:** Gradle/Android projects are never misrouted to `pytest`.
* **Honest Prerequisite Limitation Reporting:** Never fabricates fake test passes when toolchains are absent.
* **Causal Graph Evidence Integrity:** Graphs dynamically reflect genuine project files and runners without phantom fallbacks.

### Unproven Capabilities / Remaining Scope
* **Complex Multi-File Refactorings:** The model successfully fixed single-module algorithmic and logic errors. Large-scale structural refactorings spanning multiple interdependent modules remain unproven.
* **Dynamic Repair on Heavy Stacks Without Host Provisioning:** Projects requiring complex external daemons (e.g. Android Emulator, Gradle daemon, Docker-in-Docker) remain blocked at the prerequisite detection boundary unless pre-installed on the host.
* **Production Hardened OS Sandboxing:** Container-based hypervisor/cgroup process isolation for untrusted user-submitted archives is documented as an infrastructure requirement, not yet enforced on bare Windows hosts.
