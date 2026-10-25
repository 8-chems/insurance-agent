import re
import pytest
from src.graph.guard import GraphGuardError, validate
from src.graph.queries import QUERIES
from src.graph_sync.schema import TABLES, validate_event


def test_every_query_declares_all_its_parameters_and_a_limit():
    for name, q in QUERIES.items():
        used = set(re.findall(r"@(\w+)", q.gql))
        assert used == set(q.params), name
        assert "LIMIT" in q.gql, name


def test_customer_query_must_use_authenticated_customer():
    validate("list_customer_claims", {"customer_id": "c1"}, "customer", "c1")
    with pytest.raises(GraphGuardError):
        validate("list_customer_claims", {"customer_id": "c2"}, "customer", "c1")


def test_internal_query_blocked_for_customer_callers():
    with pytest.raises(GraphGuardError):
        validate("provider_group_claim_counts", {"group_id": "g"}, "customer", "c1")
    assert validate("provider_group_claim_counts", {"group_id": "g"}, "internal", None)


def test_unknown_query_and_extra_params_rejected():
    with pytest.raises(GraphGuardError):
        validate("DROP", {}, "internal", None)
    with pytest.raises(GraphGuardError):
        validate("list_customer_claims", {"customer_id": "c1", "x": "1"}, "customer", "c1")


def test_sync_event_validation():
    ok = {"table": "Claim", "op": "upsert", "pk": {"claim_id": "a"}, "values": {"status": "rejected"},
          "source_updated_at": "2026-10-20T14:00:00Z"}
    assert validate_event(ok) is TABLES["Claim"]
    with pytest.raises(ValueError):
        validate_event({**ok, "table": "Claim; DROP TABLE Claim"})
    with pytest.raises(ValueError):
        validate_event({**ok, "values": {"evil": "x"}})
    with pytest.raises(ValueError):
        validate_event({k: v for k, v in ok.items() if k != "source_updated_at"})


def test_schema_declares_every_synced_table_and_the_derived_edge():
    ddl = open("graph/schema.sql", encoding="utf-8").read()
    for table in TABLES:
        assert f"CREATE TABLE {table} " in ddl, table
    assert "CREATE TABLE ClaimAppliesVersion" in ddl and "LABEL AppliesVersion" in ddl
    assert "ClaimAppliesVersion" not in TABLES        # derived edges are never written by source events
