from google.genai import types
from pydantic import BaseModel
from src.common.config import settings
from src.verify.claims import AtomicClaim, get_client
from src.verify.evidence import Evidence


class Verdict(BaseModel):
    label: str                   # supported | unsupported | contradicted
    reason: str


class Checked(BaseModel):
    claim: AtomicClaim
    label: str
    method: str                  # deterministic | model
    reason: str


def check_claim(c: AtomicClaim, ledger: dict[str, Evidence]) -> Checked:
    if c.kind == "advice":
        return Checked(claim=c, label="unverifiable", method="deterministic", reason="advice, not a fact")
    missing = [s for s in c.cited if s not in ledger]
    if not c.cited or missing:
        return Checked(claim=c, label="unsupported", method="deterministic",
                       reason=f"no valid source ({missing or 'none cited'})")
    api = [ledger[s] for s in c.cited if ledger[s].kind == "api"]
    if c.kind == "status" and api and c.value:
        ok = c.value.strip().casefold() == str(api[0].data.get("status", "")).strip().casefold()
        return Checked(claim=c, label="supported" if ok else "contradicted", method="deterministic",
                       reason=f'record says {api[0].data.get("status")}')
    evidence = "\n".join(f'[{s}] {ledger[s].data.get("text", ledger[s].data)}' for s in c.cited)
    r = get_client().models.generate_content(
        model=settings.verifier_model,
        contents=(f"EVIDENCE:\n{evidence}\n\nCLAIM: {c.text}\n\nDoes the evidence support the claim, "
                  "contradict it, or fail to establish it? Be strict: a claim that adds a detail "
                  "not in the evidence is unsupported."),
        config=types.GenerateContentConfig(response_mime_type="application/json",
                                           response_schema=Verdict, temperature=0))
    if not r.parsed:
        return Checked(claim=c, label="unsupported", method="model", reason="verifier returned no verdict")
    return Checked(claim=c, label=r.parsed.label, method="model", reason=r.parsed.reason)
