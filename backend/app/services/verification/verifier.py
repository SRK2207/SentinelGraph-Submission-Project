from datetime import datetime, timezone
from typing import Dict, Any, Optional
from backend.app.schemas.investigation import VerificationResultModel
from backend.app.data.scenarios import get_scenario


class VerificationEngine:
    """
    Executes controlled simulated verifications against in-memory synthetic scenario state.
    Never executes real external workflows or shell commands.
    """

    @staticmethod
    def verify_remediation(
        scenario_id: str,
        option_id: str
    ) -> VerificationResultModel:
        now = datetime.now(timezone.utc).isoformat()
        scenario = get_scenario(scenario_id)
        if not scenario:
            return VerificationResultModel(
                status="failed",
                simulated=True,
                timestamp=now,
                applied_option_id=option_id,
                message=f"Scenario '{scenario_id}' not found.",
                details={"error": "Invalid scenario"}
            )

        # Find option
        options = {opt["option_id"]: opt for opt in scenario.get("remediation_options", [])}
        if option_id not in options:
            return VerificationResultModel(
                status="failed",
                simulated=True,
                timestamp=now,
                applied_option_id=option_id,
                message=f"Remediation option '{option_id}' is not recognized.",
                details={"valid_options": list(options.keys())}
            )

        chosen_opt = options[option_id]
        resolves = chosen_opt.get("resolves_failure", False)

        if scenario_id == "scenario-invoice-field-rename":
            if option_id == "opt-workflow-update":
                # Apply simulated update to synthetic in-memory workflow definition
                wf = scenario.get("workflow_definition", {})
                for step in wf.get("steps", []):
                    if step.get("step_id") == "step_3":
                        step["expected_field"] = "email"
                        step["remediated"] = True

                return VerificationResultModel(
                    status="passed",
                    simulated=True,
                    timestamp=now,
                    applied_option_id=option_id,
                    applied_option_title=chosen_opt.get("title"),
                    message=(
                        "Simulated verification passed. Workflow step 'extract_email_for_delivery' "
                        "successfully consumed field 'email' from customer payload. "
                        "Invoice PDF generated and dispatched without errors."
                    ),
                    details={
                        "workflow_id": "wf-invoice-gen-v2",
                        "field_checked": "email",
                        "field_value_found": "customer@example.test",
                        "execution_result": "200 OK - Invoice Dispatched"
                    }
                )

            elif option_id == "opt-backend-alias":
                # Apply simulated update to synthetic customer API schema
                svc = scenario.get("service", {})
                curr_schema = svc.get("current_schema", {})
                curr_schema["customer_email"] = curr_schema.get("email", "customer@example.test")
                curr_schema["alias_active"] = True

                return VerificationResultModel(
                    status="passed",
                    simulated=True,
                    timestamp=now,
                    applied_option_id=option_id,
                    applied_option_title=chosen_opt.get("title"),
                    message=(
                        "Simulated verification passed. Customer service API exposed backward-compatible "
                        "alias 'customer_email' alongside 'email'. Workflow consumed 'customer_email' successfully."
                    ),
                    details={
                        "service_id": "srv-customer-api",
                        "fields_present": ["customer_id", "email", "customer_email", "customer_name"],
                        "execution_result": "200 OK - Backward compatibility verified"
                    }
                )

            else:
                return VerificationResultModel(
                    status="failed",
                    simulated=True,
                    timestamp=now,
                    applied_option_id=option_id,
                    applied_option_title=chosen_opt.get("title"),
                    message=(
                        "Simulated verification failed. Restarting the worker did not address "
                        "the missing 'customer_email' field in the customer API response payload. "
                        "KeyError: 'customer_email' recurred upon execution."
                    ),
                    details={
                        "reproduction": "KeyError: 'customer_email'",
                        "unresolved_dependency": "customer_email"
                    }
                )

        elif scenario_id == "scenario-ambiguous-timeout":
            if option_id == "opt-retry-with-backoff":
                return VerificationResultModel(
                    status="passed",
                    simulated=True,
                    timestamp=now,
                    applied_option_id=option_id,
                    applied_option_title=chosen_opt.get("title"),
                    message=(
                        "Simulated verification passed. Configured 60s timeout and exponential backoff retry. "
                        "Subsequent simulated request succeeded on retry attempt 2."
                    ),
                    details={
                        "new_timeout": "60s",
                        "retries": 3,
                        "simulated_outcome": "Settlement batch synchronized on retry 2"
                    }
                )
            else:
                return VerificationResultModel(
                    status="failed",
                    simulated=True,
                    timestamp=now,
                    applied_option_id=option_id,
                    applied_option_title=chosen_opt.get("title"),
                    message=(
                        "Simulated verification failed. Reverting repository commits had no effect "
                        "on external settlement gateway availability. Upstream timeout persisted."
                    ),
                    details={
                        "external_endpoint": "https://settlement.partner.example.test",
                        "error": "GatewayTimeoutError: 30000ms"
                    }
                )

        return VerificationResultModel(
            status="passed" if resolves else "failed",
            simulated=True,
            timestamp=now,
            applied_option_id=option_id,
            applied_option_title=chosen_opt.get("title"),
            message="Simulated verification executed."
        )
