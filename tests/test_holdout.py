"""Held-out scenarios (never used to design the rules) must reach a safe, correct decision with perfect extraction."""
import pytest
from conftest import MANIFEST, sample
from judging import judge

from app.pipeline import run_invoice

HOLDOUT = sorted(s for s, item in MANIFEST.items() if item["set"] == "holdout")


@pytest.mark.parametrize("scenario", HOLDOUT)
def test_holdout_decision(scenario):
    pdf, extraction = sample(scenario)
    decision = run_invoice(pdf, extraction=extraction)["decision"]
    ok, why = judge(MANIFEST[scenario]["expected"], decision)
    assert ok, f"{why}: {decision['summary']}"


def test_credit_note_is_never_approved_even_if_read_as_positive():
    """If the LLM drops the minus signs and calls it an invoice, the printed words 'CREDIT NOTE' still stop it."""
    pdf, extraction = sample("T-10")
    extraction.document_type = "invoice"
    extraction.total.value = "206.94"
    extraction.total.source_quote = "$206.94"
    for line in extraction.lines:
        line.amount = abs(line.amount)
    extraction.subtotal, extraction.tax_amount = 192.50, 14.44
    decision = run_invoice(pdf, extraction=extraction)["decision"]
    assert decision["outcome"] != "Approve" and "V-06" in decision["reasons"]


def test_tax_inclusive_prices_are_compared_net_of_tax():
    pdf, extraction = sample("T-01")
    result = run_invoice(pdf, extraction=extraction)
    m01 = next(f for f in result["findings"] if f["rule"] == "M-01")
    assert m01["outcome"] == "pass" and "net of the 7.5% tax" in m01["message"]
