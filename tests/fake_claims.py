from fastapi import FastAPI, HTTPException

app = FastAPI()
DB = {"CLM-1042": {"claim_id": "CLM-1042", "customer_id": "cust-7", "status": "rejected",
                   "rejection_reason_code": "MISSING_DOCUMENT", "required_document": "itemized_invoice",
                   "last_updated": "2026-10-20T14:00:00Z"}}


@app.get("/claims/{claim_id}")
def get(claim_id: str):
    if claim_id not in DB:
        raise HTTPException(404)
    return DB[claim_id]
