from google.adk.tools import ToolContext
from src.graph.client import run_named_query
from src.graph.guard import GraphGuardError


def _run(name, params, tool_context):
    cust = tool_context.state["authenticated_customer_id"]
    try:
        out = run_named_query(name, {"customer_id": cust, **params}, caller_scope="customer", customer_id=cust)
    except GraphGuardError:
        return {"success": False, "error_code": "NOT_ALLOWED", "retryable": False}
    except Exception:
        return {"success": False, "error_code": "GRAPH_UNAVAILABLE", "retryable": True}
    return {"success": True, "source": "graph", **out}


def list_my_claims(tool_context: ToolContext) -> dict:
    """List the signed-in customer's claims with their status. Use when the customer
    asks about their claims in general, or does not give a claim id."""
    return _run("list_customer_claims", {}, tool_context)


def get_policy_version_for_claim(claim_id: str, tool_context: ToolContext) -> dict:
    """Find which policy version (document_id and version) applied on the service date of
    one of the signed-in customer's claims. Use before searching policy text for that claim."""
    return _run("policy_version_for_claim", {"claim_id": claim_id}, tool_context)
