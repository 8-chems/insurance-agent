from google.adk.agents import Agent
from src.agent.callbacks import record_evidence
from src.agent.tools.claims import get_claim_status
from src.agent.tools.policies import search_policy_documents
from src.common.config import settings

INSTRUCTION = """You are a support assistant for a health insurer.
1. For any claim question call get_claim_status. Never guess a status.
2. For coverage questions call search_policy_documents and answer only from the returned passages.
3. After every factual statement cite its evidence as [source_id], for example [claims:CLM-1042].
   Only cite ids returned by tools.
4. If a tool fails or returns not_found, say so plainly.
5. Never promise a reimbursement or perform financial actions."""

TOOLS = [get_claim_status, search_policy_documents]
if settings.enable_graph:
    from src.agent.tools.graph import get_policy_version_for_claim, list_my_claims
    TOOLS += [list_my_claims, get_policy_version_for_claim]

root_agent = Agent(
    name="insurance_assistant",
    model=settings.model_name,
    instruction=INSTRUCTION,
    tools=TOOLS,
    after_tool_callback=record_evidence,
)
