import httpx
from google.adk.tools import ToolContext
from src.common.config import settings


def get_claim_status(claim_id: str, tool_context: ToolContext) -> dict:
    """Look up the current status of one claim belonging to the signed-in
    customer. Use for any question about what happened to a claim."""
    cust = tool_context.state["authenticated_customer_id"]
    try:
        r = httpx.get(f"{settings.claims_api_url}/claims/{claim_id}", timeout=8,
                      headers={"Authorization": f"Bearer {settings.claims_api_token}"})
    except httpx.TransportError:
        return {"success": False, "error_code": "CLAIMS_UNAVAILABLE", "retryable": True}
    if r.status_code != 200 or r.json().get("customer_id") != cust:
        return {"success": True, "status": "not_found", "claim_id": claim_id}
    d = r.json()
    d.pop("customer_id")
    return {"success": True, "source": "claims_api", **d}
