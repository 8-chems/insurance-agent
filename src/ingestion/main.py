import os
import re

from fastapi import FastAPI, HTTPException, Request
from google.cloud import firestore, storage

from src.ingestion import pipeline

app = FastAPI()
db, gcs = firestore.Client(), storage.Client()
PROCESSOR = os.environ.get("DOCAI_PROCESSOR", "")
NAME = re.compile(r"policies/(?P<policy>[^/]+)/v(?P<ver>\d+)\.pdf$")


@app.get("/healthz")
def healthz():
    return {"ok": True}


@app.post("/pubsub")
async def handle(req: Request):
    a = (await req.json())["message"].get("attributes", {})
    obj, bucket, gen = a["objectId"], a["bucketId"], a["objectGeneration"]
    m = NAME.match(obj)
    if not m:
        return {"status": "ignored"}
    ref = db.collection("ingestion").document(f'{obj.replace("/", "_")}:{gen}:{pipeline.CHUNKER_VERSION}')
    snap = ref.get()
    if snap.exists and snap.to_dict()["status"] == "done":
        return {"status": "duplicate"}
    ref.set({"status": "running"})
    try:
        meta = {"effective_from": gcs.bucket(bucket).get_blob(obj).metadata["effective_from"],
                "effective_to": None}
        n = pipeline.process(f'{m["policy"]}-v{m["ver"]}', int(m["ver"]),
                             f"gs://{bucket}/{obj}", meta, PROCESSOR)
        ref.set({"status": "done", "chunks": n})
    except Exception:
        ref.set({"status": "failed"})
        raise HTTPException(500)
    return {"status": "ok"}
