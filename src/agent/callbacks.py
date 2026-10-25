import hashlib
import json
from datetime import datetime, timezone


def record_evidence(tool, args, tool_context, tool_response):
    """Copy every tool result into the evidence ledger kept in session state."""
    now = datetime.now(timezone.utc).isoformat()
    ledger = list(tool_context.state.get("evidence", []))
    if tool.name == "get_claim_status" and tool_response.get("success"):
        ledger.append({"source_id": f'claims:{tool_response["claim_id"]}', "kind": "api",
                       "title": "Claims system", "retrieved_at": now, "data": tool_response})
    if tool.name == "search_policy_documents":
        for p in tool_response.get("passages", []):
            ledger.append({"source_id": p["source_id"], "kind": "policy", "title": "Health policy",
                           "version": p["version"], "section": p["section"], "page": p["page"],
                           "retrieved_at": now, "data": {"text": p["text"]}})
    if tool.name in ("list_my_claims", "get_policy_version_for_claim") and tool_response.get("success"):
        digest = hashlib.sha1(json.dumps([tool.name, args], sort_keys=True).encode()).hexdigest()[:8]
        ledger.append({"source_id": f"graph:{tool.name}:{digest}", "kind": "graph", "title": "Relationship graph",
                       "retrieved_at": now, "data": tool_response})
    tool_context.state["evidence"] = ledger
    return None
