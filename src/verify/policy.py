from google.genai import types
from src.common.config import settings
from src.verify.check import check_claim
from src.verify.claims import extract_claims, get_client

ABSTAIN = ("I can't confirm that from the claim record and policy documents I can access. "
           "Please contact an advisor, who can check it with you.")


def decide(checked) -> str:
    labels = {c.label for c in checked}
    return "fix" if labels & {"contradicted", "unsupported"} else "allow"


def rewrite_with_gemini(draft: str, flagged) -> str:
    problems = "\n".join(f"- {c.claim.text} ({c.label}: {c.reason})" for c in flagged)
    r = get_client().models.generate_content(
        model=settings.verifier_model, config=types.GenerateContentConfig(temperature=0),
        contents=("Rewrite the answer so that it no longer contains the flagged claims, or states them "
                  "correctly. Keep every other sentence and its [source ids]. Add nothing new.\n\n"
                  f"FLAGGED:\n{problems}\n\nANSWER:\n{draft}"))
    return r.text


def verify_answer(draft: str, ledger: dict, rewrite=rewrite_with_gemini):
    checked = [check_claim(c, ledger) for c in extract_claims(draft)]
    if decide(checked) == "allow":
        return draft, "answered", checked
    flagged = [c for c in checked if c.label in {"unsupported", "contradicted"}]
    fixed = rewrite(draft, flagged)
    checked2 = [check_claim(c, ledger) for c in extract_claims(fixed)]
    if decide(checked2) == "allow":
        return fixed, "answered_after_fix", checked2
    return ABSTAIN, "abstained", checked2
