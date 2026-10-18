# SentinelGraph API Documentation

## Base URL
Default local development backend: `http://localhost:8000`

---

## Endpoints

### 1. Health & Configuration Check
`GET /api/health`

Returns server health, operational status, and active AI mode.

**Response (200 OK):**
```json
{
  "status": "healthy",
  "service": "SentinelGraph Backend",
  "version": "1.0.0",
  "mode": "AI AGENT MODE",
  "gemini_model": "gemini-2.5-flash",
  "gemini_configured": true
}
```

---

### 2. Dashboard Statistics
`GET /api/dashboard`

Retrieves KPI statistics, active connection counts, and recent investigations history.

**Response (200 OK):**
```json
{
  "total_investigations": 2,
  "resolved_investigations": 1,
  "unresolved_investigations": 1,
  "active_connections": 4,
  "mode_available": "AI AGENT MODE",
  "gemini_model_configured": "gemini-2.5-flash",
  "recent_investigations": [
    {
      "investigation_id": "INV-A1B2C3",
      "scenario_id": "scenario-invoice-field-rename",
      "mode": "AI AGENT MODE",
      "status": "completed",
      "workflow": "wf-invoice-gen-v2",
      "timestamp": "2026-10-11T09:35:00Z",
      "root_cause": "Backend API Field Rename Contract Break",
      "confidence_label": "High Confidence"
    }
  ]
}
```

---

### 3. Simulated Connection Status
`GET /api/connections`

Lists simulated integrations (Repository, APIs, Schema Registries, Workflow Engines).

**Response (200 OK):**
```json
[
  {
    "id": "conn-git-repo",
    "name": "Source Repository (Git)",
    "type": "Version Control System",
    "status": "MOCK DATA",
    "description": "Simulated Git repository index containing recent commits, authors, and schema diffs.",
    "last_sync": "2026-10-11 09:30:00 UTC",
    "records_available": 3
  }
]
```

---

### 4. Available Demonstration Scenarios
`GET /api/scenarios`

Lists available demonstration scenarios.

**Response (200 OK):**
```json
[
  {
    "id": "scenario-invoice-field-rename",
    "name": "Invoice Workflow Failure — Backend Field Rename",
    "category": "Contract Incompatibility",
    "description": "Invoice generation failed because a backend API response field was renamed.",
    "difficulty": "Standard",
    "workflow_name": "Invoice Customer Dispatcher",
    "error_message": "KeyError: 'customer_email' - Required field customer_email was not found in customer response.",
    "timestamp": "2026-10-11T09:30:15Z"
  },
  {
    "id": "scenario-ambiguous-timeout",
    "name": "Payment Reconciliation Timeout — Ambiguous Cause",
    "category": "External Infrastructure Timeout",
    "description": "Daily payment reconciliation failed due to upstream gateway timeout.",
    "difficulty": "Ambiguous / Insufficient Evidence",
    "workflow_name": "Daily Payment Reconciler",
    "error_message": "GatewayTimeoutError: Upstream payment settlement gateway timed out after 30000ms.",
    "timestamp": "2026-10-11T08:00:20Z"
  }
]
```

---

### 5. Launch Investigation
`POST /api/investigations`

Starts an autonomous investigation run using either the Gemini Agent or Deterministic Demo Mode.

**Request Body:**
```json
{
  "scenario_id": "scenario-invoice-field-rename",
  "force_deterministic": false
}
```

**Response (201 Created):**
```json
{
  "investigation_id": "INV-D4E5F6",
  "scenario_id": "scenario-invoice-field-rename",
  "mode": "AI AGENT MODE",
  "status": "completed",
  "message": "Investigation completed successfully."
}
```

---

### 6. Investigation Timeline Events
`GET /api/investigations/{investigation_id}/events`

Returns ordered timeline events, tool selection history, and input/output payloads.

**Response (200 OK):**
```json
[
  {
    "event_id": "evt-1",
    "timestamp": "2026-10-11T09:35:01Z",
    "stage": "Dynamic Tool Selection",
    "type": "tool_call",
    "message": "Gemini selected tool: get_failure_details",
    "tool_name": "get_failure_details",
    "tool_args": { "scenario_id": "scenario-invoice-field-rename" },
    "tool_result": { "status": "success", "failure_id": "FAIL-9021" },
    "is_gemini_native": true
  }
]
```

---

### 7. Causal Dependency Graph
`GET /api/investigations/{investigation_id}/graph`

Returns directed graph elements formatted for React Flow rendering.

**Response (200 OK):**
```json
{
  "nodes": [
    {
      "id": "node-commit-4f8a12d",
      "type": "customSentinel",
      "position": { "x": 50, "y": 120 },
      "data": {
        "label": "Commit 4f8a12d (Rename)",
        "component_type": "commit",
        "status": "confirmed",
        "explanation": "Commit 4f8a12d refactored customer API.",
        "evidence_ids": ["EVID-DIFF-4f8a12d"],
        "metadata": { "file": "services/customer/api.py" }
      }
    }
  ],
  "edges": [
    {
      "id": "edge-1",
      "source": "node-commit-4f8a12d",
      "target": "node-api-schema",
      "label": "modified",
      "relationship": "modified",
      "animated": true
    }
  ]
}
```

---

### 8. Full Investigation Report
`GET /api/investigations/{investigation_id}/report`

Returns the complete structured findings, root cause, evidence references, and recommendations.

**Response (200 OK):**
```json
{
  "investigation_id": "INV-D4E5F6",
  "scenario_id": "scenario-invoice-field-rename",
  "mode": "AI AGENT MODE",
  "status": "completed",
  "summary": "Investigation confirmed a cross-system breaking contract change...",
  "failure": {
    "failure_id": "FAIL-9021",
    "title": "Invoice Customer Dispatcher Failure",
    "description": "KeyError: 'customer_email'...",
    "workflow_id": "wf-invoice-gen-v2",
    "affected_component": "invoice-generator",
    "timestamp": "2026-10-11T09:30:15Z",
    "error_message": "KeyError: 'customer_email'"
  },
  "root_cause": {
    "title": "Backend API Field Rename Contract Break",
    "explanation": "Commit 4f8a12d changed JSON response key...",
    "confidence": 0.96,
    "confidence_label": "High Confidence",
    "status": "probable",
    "evidence_ids": ["EVID-DIFF-4f8a12d", "EVID-CONTRACT-customer_email"]
  },
  "causal_chain": [
    "Commit 4f8a12d refactored customer API",
    "Customer API response key renamed: customer_email -> email",
    "Invoice workflow step 3 expected customer_email",
    "KeyError raised during invoice generation"
  ],
  "affected_components": [
    "services/customer/api.py",
    "wf-invoice-gen-v2"
  ],
  "recommendations": [
    {
      "option_id": "opt-workflow-update",
      "title": "Update Workflow Field Mapping",
      "target": "wf-invoice-gen-v2",
      "description": "Update invoice workflow step 3 to consume 'email'.",
      "trade_offs": "Localized fix; requires updating other consumers.",
      "resolves_failure": true
    }
  ],
  "verification": {
    "status": "not_run",
    "simulated": true,
    "notice": "SIMULATED VERIFICATION — NO REAL WORKFLOW EXECUTED",
    "message": "Remediation not yet applied."
  }
}
```

---

### 9. Apply Remediation
`POST /api/investigations/{investigation_id}/remediation`

Applies a chosen remediation option to the in-memory scenario state and runs simulated verification.

**Request Body:**
```json
{
  "option_id": "opt-workflow-update"
}
```

---

### 10. Run Simulated Verification
`POST /api/investigations/{investigation_id}/verify`

Executes verification checks against the simulated in-memory state.

**Response (200 OK):**
```json
{
  "status": "passed",
  "simulated": true,
  "notice": "SIMULATED VERIFICATION — NO REAL WORKFLOW EXECUTED",
  "timestamp": "2026-10-11T09:40:00Z",
  "applied_option_id": "opt-workflow-update",
  "applied_option_title": "Update Workflow Field Mapping",
  "message": "Simulated verification passed. Workflow step 'extract_email_for_delivery' successfully consumed field 'email'.",
  "details": {
    "workflow_id": "wf-invoice-gen-v2",
    "field_checked": "email",
    "field_value_found": "customer@example.test",
    "execution_result": "200 OK - Invoice Dispatched"
  }
}
```

---

### 11. Reset State
`POST /api/demo/reset`

Clears cached investigations and resets synthetic fixtures to default state.

**Response (200 OK):**
```json
{
  "status": "success",
  "message": "Synthetic demonstration fixtures and investigation states successfully reset."
}
```
