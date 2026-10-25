"""Pure-Python checks that run before any graph query leaves the application."""
from src.graph.queries import QUERIES, NamedQuery


class GraphGuardError(Exception):
    pass


def validate(name: str, params: dict, caller_scope: str, customer_id: str | None) -> NamedQuery:
    q = QUERIES.get(name)
    if q is None:
        raise GraphGuardError("unknown query")
    if q.scope == "internal" and caller_scope != "internal":
        raise GraphGuardError("query not allowed for this caller")
    if set(params) != set(q.params):
        raise GraphGuardError("unexpected or missing parameters")
    if q.scope == "customer":
        if not customer_id or params.get("customer_id") != customer_id:
            raise GraphGuardError("customer mismatch")
    return q
