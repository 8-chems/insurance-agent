import os
import re

from google.cloud import storage

from src.ingestion import pipeline

idx = int(os.environ.get("CLOUD_RUN_TASK_INDEX", 0))
n = int(os.environ.get("CLOUD_RUN_TASK_COUNT", 1))
bucket, processor = os.environ["SOURCE_BUCKET"], os.environ["DOCAI_PROCESSOR"]
NAME = re.compile(r"policies/(?P<policy>[^/]+)/v(?P<ver>\d+)\.pdf$")

blobs = sorted((b for b in storage.Client().list_blobs(bucket, prefix="policies/") if NAME.match(b.name)),
               key=lambda b: b.name)
for b in blobs[idx::n]:                                  # this task's share only
    m = NAME.match(b.name)
    meta = {"effective_from": (b.metadata or {})["effective_from"], "effective_to": None}
    pipeline.process(f'{m["policy"]}-v{m["ver"]}', int(m["ver"]), f"gs://{bucket}/{b.name}", meta, processor)
    print({"task": idx, "document": b.name})
