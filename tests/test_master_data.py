"""Invoices whose master data is missing, or borrowed from someone else's records."""
from conftest import sample

from app.pipeline import run_invoice


def findings_by_rule(result: dict) -> dict:
    return {f["rule"]: f for f in result["findings"]}


def test_nothing_in_master_data_is_held_for_procurement_and_cannot_be_approved():
    pdf, extraction = sample("T-11")
    result = run_invoice(pdf, extraction=extraction)
    assert result["decision"]["outcome"] == "Review" and result["decision"]["owner"] == "Procurement"
    assert {"VM-01", "P-01"} <= set(result["decision"]["reasons"])
    assert result["vendor"] is None and result["po"] is None        # the UI disables Approve on this basis


def test_unknown_vendor_quoting_our_real_po_is_a_high_risk_hold():
    pdf, extraction = sample("T-11")
    extraction.po_number.value = extraction.po_number.source_quote = "PO-4501"   # Apex Fasteners' real PO
    result = run_invoice(pdf, extraction=extraction)
    p02 = findings_by_rule(result)["P-02"]
    assert p02["outcome"] == "review" and p02["severity"] == "high" and "Apex Fasteners" in p02["message"]
    assert result["decision"]["severity"] == "high" and result["decision"]["owner"] == "AP lead"


def test_checks_with_nothing_to_compare_are_not_reported_as_passed():
    pdf, extraction = sample("T-11")
    extraction.po_number.value = extraction.po_number.source_quote = "PO-4501"
    rules = findings_by_rule(run_invoice(pdf, extraction=extraction))
    assert "M-00" in rules and not {"M-01", "M-02", "M-03", "M-04", "M-05"} & set(rules)
