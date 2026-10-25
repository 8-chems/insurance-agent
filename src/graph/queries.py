"""The ONLY graph queries the application may run. The language model never writes GQL."""
from dataclasses import dataclass


@dataclass(frozen=True)
class NamedQuery:
    gql: str
    params: dict          # parameter name -> "STRING" | "INT64" | "DATE"
    columns: tuple
    scope: str            # "customer": must be anchored on the authenticated customer; "internal": staff tools only
    max_rows: int = 50


QUERIES = {
    "list_customer_claims": NamedQuery(
        gql="""GRAPH InsuranceGraph
MATCH (c:Customer {customer_id: @customer_id})-[:Owns]->(p:Policy)-[:HasClaim]->(cl:Claim)
RETURN cl.claim_id AS claim_id, cl.status AS status, p.policy_id AS policy_id
ORDER BY cl.submitted_at DESC
LIMIT 50""",
        params={"customer_id": "STRING"}, columns=("claim_id", "status", "policy_id"), scope="customer"),

    # The graph answers "which policy VERSION applied on the service date"; Part 2 retrieval then
    # filters kb.chunks by that document_id, so the right clause is quoted.
    "policy_version_for_claim": NamedQuery(
        gql="""GRAPH InsuranceGraph
MATCH (c:Customer {customer_id: @customer_id})-[:Owns]->(p:Policy)-[:HasClaim]->(cl:Claim {claim_id: @claim_id})
MATCH (p)-[:HasVersion]->(v:PolicyVersion)
FILTER v.effective_from <= cl.service_date AND (v.effective_to IS NULL OR v.effective_to >= cl.service_date)
RETURN v.document_id AS document_id, v.version AS version, cl.service_date AS service_date
LIMIT 5""",
        params={"customer_id": "STRING", "claim_id": "STRING"},
        columns=("document_id", "version", "service_date"), scope="customer", max_rows=5),

    # Cross-customer pattern: AGGREGATES only, never other customers' claims. Staff tools only.
    "provider_group_claim_counts": NamedQuery(
        gql="""GRAPH InsuranceGraph
MATCH (g:ProviderGroup {group_id: @group_id})<-[:MemberOf]-(pr:Provider)<-[:ByProvider]-(cl:Claim)
FILTER cl.submitted_at >= TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 90 DAY)
RETURN pr.provider_id AS provider_id, COUNT(cl) AS claims_90d
GROUP BY pr.provider_id
ORDER BY claims_90d DESC
LIMIT 50""",
        params={"group_id": "STRING"}, columns=("provider_id", "claims_90d"), scope="internal"),
}
