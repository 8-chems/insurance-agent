"""Idempotent, order-safe upserts into Spanner. Table and column names come ONLY from schema.TABLES."""
from google.cloud.spanner_v1 import param_types

from src.graph_sync.schema import TABLES, validate_event

T = {"STRING": param_types.STRING, "INT64": param_types.INT64, "DATE": param_types.DATE,
     "TIMESTAMP": param_types.TIMESTAMP}


def apply_event(txn, ev: dict) -> str:
    spec = validate_event(ev)
    table, pk, ts = ev["table"], ev["pk"], ev["source_updated_at"]
    cols = spec["cols"]
    where = " AND ".join(f"{c} = @{c}" for c in spec["pk"])
    if ev["op"] == "delete":
        txn.execute_update(f"DELETE FROM {table} WHERE {where} AND source_updated_at <= @source_updated_at",
                           params={**pk, "source_updated_at": ts},
                           param_types={**{c: T[cols[c]] for c in pk}, "source_updated_at": T["TIMESTAMP"]})
        return "deleted"
    data = {**pk, **ev.get("values", {}), "source_updated_at": ts}
    names = list(data)
    ptypes = {c: T[cols[c]] for c in names}
    # 1) create the row if it does not exist, 2) update it only if this event is newer than what is stored
    txn.execute_update(f"INSERT OR IGNORE INTO {table} ({', '.join(names)}) VALUES ({', '.join('@' + c for c in names)})",
                       params=data, param_types=ptypes)
    sets = ", ".join(f"{c} = @{c}" for c in names if c not in spec["pk"])
    n = txn.execute_update(f"UPDATE {table} SET {sets} WHERE {where} AND source_updated_at < @source_updated_at",
                           params=data, param_types=ptypes)
    return "updated" if n else "ignored_or_inserted"
