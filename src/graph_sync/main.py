import base64
import json

from fastapi import FastAPI, HTTPException, Request
from google.cloud import spanner

from src.common.config import settings
from src.graph_sync.upsert import apply_event

app = FastAPI()
_db = spanner.Client().instance(settings.spanner_instance).database(settings.spanner_database)


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/pubsub")
async def handle(req: Request):
    msg = (await req.json())["message"]
    try:
        ev = json.loads(base64.b64decode(msg["data"]))
        result = _db.run_in_transaction(lambda txn: apply_event(txn, ev))
    except ValueError:
        return {"status": "rejected"}        # malformed event: acknowledge so it is not retried forever
    except Exception:
        raise HTTPException(500)             # transient failure: Pub/Sub retries, then dead-letters
    print(json.dumps({"severity": "INFO", "event": "graph_sync", "table": ev["table"], "result": result,
                      "source_updated_at": ev["source_updated_at"]}))
    return {"status": result}
