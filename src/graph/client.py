from datetime import timedelta
from functools import lru_cache

from google.cloud import spanner
from google.cloud.spanner_v1 import param_types

from src.common.config import settings
from src.graph.guard import validate

TYPES = {"STRING": param_types.STRING, "INT64": param_types.INT64, "DATE": param_types.DATE}


@lru_cache(maxsize=1)
def _database():
    return spanner.Client().instance(settings.spanner_instance).database(settings.spanner_database)


def run_named_query(name: str, params: dict, *, caller_scope: str, customer_id: str | None = None,
                    timeout_s: float = 5.0) -> dict:
    q = validate(name, params, caller_scope, customer_id)
    # Bounded-staleness read: cheaper and faster than a strong read. Relationships may lag by seconds;
    # decisions about money or status re-read the authoritative system instead.
    with _database().snapshot(exact_staleness=timedelta(seconds=10)) as snap:
        result = snap.execute_sql(q.gql, params=params,
                                  param_types={k: TYPES[v] for k, v in q.params.items()}, timeout=timeout_s)
        rows = []
        for r in result:
            rows.append([str(v) if v is not None and not isinstance(v, (int, float, str)) else v for v in r])
            if len(rows) >= q.max_rows:
                break
    return {"columns": list(q.columns), "rows": rows}
