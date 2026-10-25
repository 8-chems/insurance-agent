import os
import httpx
import pytest

URL = os.environ.get("STAGING_URL")
pytestmark = pytest.mark.skipif(not URL, reason="set STAGING_URL, TOKEN_CUST_A, TOKEN_CUST_B")


def chat(token, msg):
    h = {"Authorization": f"Bearer {token}"}
    if os.environ.get("GCP_ID_TOKEN"):
        h["X-Serverless-Authorization"] = f"Bearer {os.environ['GCP_ID_TOKEN']}"
    return httpx.post(f"{URL}/api/v1/chat", headers=h, json={"message": msg}, timeout=90)


def test_no_token_is_rejected():
    assert chat("", "hi").status_code == 401


def test_garbage_token_is_rejected():
    assert chat("abc.def.ghi", "hi").status_code == 401


def test_customer_cannot_read_others_claim():
    r = chat(os.environ["TOKEN_CUST_B"], "What is the status of claim CLM-1042?")
    assert "rejected" not in r.text.lower() and "invoice" not in r.text.lower()
