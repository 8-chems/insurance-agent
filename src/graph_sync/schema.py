"""Allow-list of tables and columns the sync is allowed to write (pure Python, no GCP imports)."""

TABLES = {
    "Customer": {"pk": ["customer_id"], "cols": {"customer_id": "STRING", "region": "STRING", "source_updated_at": "TIMESTAMP"}},
    "Policy": {"pk": ["policy_id"], "cols": {"policy_id": "STRING", "product": "STRING", "source_updated_at": "TIMESTAMP"}},
    "PolicyVersion": {"pk": ["policy_version_id"], "cols": {"policy_version_id": "STRING", "policy_id": "STRING",
        "version": "INT64", "document_id": "STRING", "effective_from": "DATE", "effective_to": "DATE",
        "source_updated_at": "TIMESTAMP"}},
    "Claim": {"pk": ["claim_id"], "cols": {"claim_id": "STRING", "status": "STRING", "service_date": "DATE",
        "submitted_at": "TIMESTAMP", "source_updated_at": "TIMESTAMP"}},
    "Provider": {"pk": ["provider_id"], "cols": {"provider_id": "STRING", "source_updated_at": "TIMESTAMP"}},
    "ProviderGroup": {"pk": ["group_id"], "cols": {"group_id": "STRING", "source_updated_at": "TIMESTAMP"}},
    "CustomerOwnsPolicy": {"pk": ["customer_id", "policy_id"], "cols": {"customer_id": "STRING", "policy_id": "STRING", "source_updated_at": "TIMESTAMP"}},
    "PolicyHasVersion": {"pk": ["policy_id", "policy_version_id"], "cols": {"policy_id": "STRING", "policy_version_id": "STRING", "source_updated_at": "TIMESTAMP"}},
    "PolicyHasClaim": {"pk": ["policy_id", "claim_id"], "cols": {"policy_id": "STRING", "claim_id": "STRING", "source_updated_at": "TIMESTAMP"}},
    "ClaimByProvider": {"pk": ["claim_id", "provider_id"], "cols": {"claim_id": "STRING", "provider_id": "STRING", "source_updated_at": "TIMESTAMP"}},
    "ProviderMemberOf": {"pk": ["provider_id", "group_id"], "cols": {"provider_id": "STRING", "group_id": "STRING", "source_updated_at": "TIMESTAMP"}},
}


def validate_event(ev: dict) -> dict:
    spec = TABLES.get(ev.get("table"))
    if spec is None:
        raise ValueError("unknown table")
    if ev.get("op") not in ("upsert", "delete"):
        raise ValueError("unknown op")
    values = ev.get("values", {})
    if set(values) - set(spec["cols"]) or set(ev.get("pk", {})) != set(spec["pk"]):
        raise ValueError("unexpected columns or key")
    if "source_updated_at" not in ev:
        raise ValueError("source_updated_at is required")
    return spec
