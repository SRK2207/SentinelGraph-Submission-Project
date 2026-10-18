from typing import Dict, Any, Optional, List
from backend.app.data.scenarios import get_scenario


def get_failure_details(scenario_id: str, **kwargs) -> Dict[str, Any]:
    """
    Retrieve structured failure details for the workflow incident.
    Returns the failure ID, timestamp, error message, affected workflow,
    stack trace, and execution context.
    """
    target_id = scenario_id or kwargs.get("scenario") or kwargs.get("id") or ""
    if not target_id or not isinstance(target_id, str):
        return {"status": "error", "error": "Invalid scenario_id provided. Must be a non-empty string."}
        
    scenario = get_scenario(target_id.strip())
    if not scenario:
        return {"status": "error", "error": f"Scenario '{target_id}' not found."}
        
    failure = scenario.get("failure", {})
    return {
        "status": "success",
        "scenario_id": target_id.strip(),
        "failure_id": failure.get("failure_id"),
        "timestamp": failure.get("timestamp"),
        "workflow_id": failure.get("workflow_id"),
        "workflow_name": failure.get("workflow_name"),
        "affected_component": failure.get("affected_component"),
        "error_type": failure.get("error_type"),
        "error_message": failure.get("error_message"),
        "execution_id": failure.get("execution_id"),
        "environment": failure.get("environment"),
        "stack_trace": failure.get("stack_trace")
    }


def get_recent_commits(scenario_id: str, limit: int = 5, **kwargs) -> Dict[str, Any]:
    """
    Retrieve recent repository commits leading up to the failure incident.
    Returns commit hashes, authors, timestamps, commit messages, and modified files.
    """
    target_id = scenario_id or kwargs.get("scenario") or kwargs.get("id") or ""
    if not target_id or not isinstance(target_id, str):
        return {"status": "error", "error": "Invalid scenario_id provided. Must be a non-empty string."}
        
    scenario = get_scenario(target_id.strip())
    if not scenario:
        return {"status": "error", "error": f"Scenario '{target_id}' not found."}
        
    raw_limit = limit
    for alias in ["count", "n", "max_commits", "max_results"]:
        if alias in kwargs:
            raw_limit = kwargs[alias]
            break

    try:
        parsed_limit = int(raw_limit)
    except (ValueError, TypeError):
        parsed_limit = 5

    safe_limit = max(1, min(parsed_limit, 10))
    commits = scenario.get("recent_commits", [])
    return {
        "status": "success",
        "scenario_id": target_id.strip(),
        "total_commits": len(commits),
        "commits": commits[:safe_limit]
    }


def get_dependency_info(scenario_id: str, workflow_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Retrieve cross-system dependency relationships between the workflow,
    upstream services, downstream workers, and field contracts.
    """
    target_id = scenario_id or kwargs.get("scenario") or kwargs.get("id") or ""
    if not target_id or not isinstance(target_id, str):
        return {"status": "error", "error": "Invalid scenario_id provided. Must be a non-empty string."}
        
    scenario = get_scenario(target_id.strip())
    if not scenario:
        return {"status": "error", "error": f"Scenario '{target_id}' not found."}
        
    dependencies = scenario.get("dependencies", {})
    return {
        "status": "success",
        "scenario_id": target_id.strip(),
        "workflow_id": dependencies.get("workflow_id"),
        "upstream_services": dependencies.get("upstream_services", []),
        "downstream_components": dependencies.get("downstream_components", []),
        "field_contracts": dependencies.get("field_contracts", [])
    }


def get_workflow_definition(scenario_id: str, workflow_id: Optional[str] = None, **kwargs) -> Dict[str, Any]:
    """
    Retrieve the automation workflow definition, including its sequence of steps,
    actions, field requirements, and expected payload schemas.
    """
    target_id = scenario_id or kwargs.get("scenario") or kwargs.get("id") or ""
    if not target_id or not isinstance(target_id, str):
        return {"status": "error", "error": "Invalid scenario_id provided. Must be a non-empty string."}
        
    scenario = get_scenario(target_id.strip())
    if not scenario:
        return {"status": "error", "error": f"Scenario '{target_id}' not found."}
        
    workflow = scenario.get("workflow_definition", {})
    return {
        "status": "success",
        "scenario_id": target_id.strip(),
        "workflow_id": workflow.get("workflow_id"),
        "name": workflow.get("name"),
        "description": workflow.get("description"),
        "trigger": workflow.get("trigger"),
        "steps": workflow.get("steps", [])
    }


def inspect_commit(scenario_id: str, commit_id: str = "", **kwargs) -> Dict[str, Any]:
    """
    Inspect the exact diff, modified files, and code changes introduced by a specific commit.
    """
    target_id = scenario_id or kwargs.get("scenario") or kwargs.get("id") or ""
    if not target_id or not isinstance(target_id, str):
        return {"status": "error", "error": "Invalid scenario_id provided. Must be a non-empty string."}
        
    raw_commit = commit_id or kwargs.get("commit_hash") or kwargs.get("commit") or kwargs.get("sha") or kwargs.get("hash") or ""
    if not raw_commit or not isinstance(raw_commit, str) or not raw_commit.strip():
        return {"status": "error", "error": "Invalid commit_id provided. Must be a non-empty string."}
        
    scenario = get_scenario(target_id.strip())
    if not scenario:
        return {"status": "error", "error": f"Scenario '{target_id}' not found."}
        
    diffs = scenario.get("commit_diffs", {})
    clean_commit_id = raw_commit.strip()
    
    if clean_commit_id not in diffs:
        # Search if partial match
        matching = [c for c in diffs.keys() if c.startswith(clean_commit_id) or clean_commit_id.startswith(c)]
        if matching:
            clean_commit_id = matching[0]
        else:
            return {
                "status": "error",
                "message": f"Commit '{clean_commit_id}' not found in scenario repository history."
            }
            
    diff_data = diffs[clean_commit_id]
    return {
        "status": "success",
        "scenario_id": target_id.strip(),
        "commit_id": clean_commit_id,
        "file": diff_data.get("file"),
        "diff": diff_data.get("diff"),
        "description": diff_data.get("description")
    }


# Registry of available tools for Gemini function declaration and execution dispatch
INVESTIGATION_TOOL_FUNCTIONS = {
    "get_failure_details": get_failure_details,
    "get_recent_commits": get_recent_commits,
    "get_dependency_info": get_dependency_info,
    "get_workflow_definition": get_workflow_definition,
    "inspect_commit": inspect_commit,
}
