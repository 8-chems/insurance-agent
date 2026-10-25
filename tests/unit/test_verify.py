from src.verify.check import check_claim
from src.verify.cite import render
from src.verify.claims import AtomicClaim
from src.verify.evidence import Evidence
from src.verify.policy import decide

LEDGER = {"claims:CLM-1042": Evidence(source_id="claims:CLM-1042", kind="api", title="Claims system",
                                      retrieved_at="t", data={"status": "rejected"})}


def status_claim(value, cited=("claims:CLM-1042",)):
    return AtomicClaim(text="x", cited=list(cited), kind="status", value=value)


def test_status_supported():
    assert check_claim(status_claim("rejected"), LEDGER).label == "supported"


def test_status_contradicted():
    assert check_claim(status_claim("approved"), LEDGER).label == "contradicted"


def test_unknown_source_unsupported():
    assert check_claim(status_claim("rejected", ("claims:FAKE",)), LEDGER).label == "unsupported"


def test_render_drops_invented_ids():
    text, sources = render("ok [claims:FAKE] [claims:CLM-1042]", LEDGER)
    assert "FAKE" not in text and len(sources) == 1


def test_decide():
    ok = check_claim(status_claim("rejected"), LEDGER)
    bad = check_claim(status_claim("approved"), LEDGER)
    assert decide([ok]) == "allow" and decide([ok, bad]) == "fix"
