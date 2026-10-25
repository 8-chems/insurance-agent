import os
from functools import lru_cache
from google import genai
from google.genai import types
from pydantic import BaseModel
from src.common.config import settings


@lru_cache(maxsize=1)
def get_client() -> genai.Client:
    return genai.Client(vertexai=True, project=os.environ["GOOGLE_CLOUD_PROJECT"],
                        location=os.environ.get("GOOGLE_CLOUD_LOCATION", settings.region))


class AtomicClaim(BaseModel):
    text: str
    cited: list[str]
    kind: str                    # status | policy_fact | amount | advice
    value: str | None = None


class ClaimList(BaseModel):
    claims: list[AtomicClaim]


def extract_claims(draft: str) -> list[AtomicClaim]:
    r = get_client().models.generate_content(
        model=settings.verifier_model,
        contents=("Split the answer into single, self-contained factual claims. Keep the "
                  "[source ids] cited for each claim. Mark promises and recommendations as "
                  "kind=advice.\n\nANSWER:\n" + draft),
        config=types.GenerateContentConfig(response_mime_type="application/json",
                                           response_schema=ClaimList, temperature=0))
    return r.parsed.claims if r.parsed else []
