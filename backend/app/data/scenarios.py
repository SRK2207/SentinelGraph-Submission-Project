import json
from pathlib import Path
from typing import Dict, Any, Optional
import copy

FIXTURES_DIR = Path(__file__).parent / "fixtures"

# In-memory store of loaded scenarios so simulated remediation can mutate in-memory state
_DEFAULT_SCENARIOS: Dict[str, Dict[str, Any]] = {}
_ACTIVE_SCENARIOS: Dict[str, Dict[str, Any]] = {}


def _load_all_fixtures() -> Dict[str, Dict[str, Any]]:
    scenarios = {}
    for file_path in FIXTURES_DIR.glob("*.json"):
        try:
            with open(file_path, "r", encoding="utf-8") as f:
                data = json.load(f)
                scenarios[data["id"]] = data
        except Exception as e:
            print(f"Error loading fixture {file_path}: {e}")
    return scenarios


def get_scenario(scenario_id: str) -> Optional[Dict[str, Any]]:
    global _ACTIVE_SCENARIOS, _DEFAULT_SCENARIOS
    if not _DEFAULT_SCENARIOS:
        reset_all_scenarios()
    
    if scenario_id in _ACTIVE_SCENARIOS:
        return _ACTIVE_SCENARIOS[scenario_id]
    return None


def get_all_scenarios() -> Dict[str, Dict[str, Any]]:
    global _ACTIVE_SCENARIOS, _DEFAULT_SCENARIOS
    if not _DEFAULT_SCENARIOS:
        reset_all_scenarios()
    return _ACTIVE_SCENARIOS


def reset_all_scenarios() -> None:
    global _ACTIVE_SCENARIOS, _DEFAULT_SCENARIOS
    _DEFAULT_SCENARIOS = _load_all_fixtures()
    _ACTIVE_SCENARIOS = copy.deepcopy(_DEFAULT_SCENARIOS)


def reset_scenario(scenario_id: str) -> Optional[Dict[str, Any]]:
    global _ACTIVE_SCENARIOS, _DEFAULT_SCENARIOS
    if scenario_id in _DEFAULT_SCENARIOS:
        _ACTIVE_SCENARIOS[scenario_id] = copy.deepcopy(_DEFAULT_SCENARIOS[scenario_id])
        return _ACTIVE_SCENARIOS[scenario_id]
    return None
