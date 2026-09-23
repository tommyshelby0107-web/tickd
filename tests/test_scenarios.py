"""Every demo scenario must reach the decision the design pack promises, for the right reason."""
import pytest
from conftest import MANIFEST, sample

from app import db
from app.pipeline import run_invoice


def run(scenario: str) -> dict:
    pdf, extraction = sample(scenario)
    return run_invoice(pdf, extraction=extraction)


@pytest.mark.parametrize("scenario", ["HP-1", "HP-2", "EC-1A", "EC-1B", "EC-3", "EC-4", "RV-1", "X-1", "X-2"])
def test_expected_decision(scenario):
    expected = MANIFEST[scenario]["expected"]
    decision = run(scenario)["decision"]
    assert decision["outcome"] == expected["decision"], decision["summary"]
    if expected["decision"] != "Approve":
        assert set(expected["rules"]) <= set(decision["reasons"]), decision["reasons"]
    if "owner" in expected:
        assert decision["owner"] == expected["owner"]


def test_duplicate_rescan_is_rejected_after_original_is_approved():
    assert run("HP-1")["decision"]["outcome"] == "Approve"
    result = run("EC-2")
    assert result["decision"]["outcome"] == "Reject"
    assert "D-02" in result["decision"]["reasons"]


def test_same_file_twice_is_rejected():
    assert run("HP-1")["decision"]["outcome"] == "Approve"
    assert "D-01" in run("HP-1")["decision"]["reasons"]


def test_approval_consumes_po_quantities():
    run("HP-1")
    lines = db.purchase_order("PO-4501")["lines"]
    assert [l["qty_invoiced"] for l in lines] == [40, 25, 10]


def test_inferred_po_is_suggested_not_approved():
    result = run("EC-3")
    assert result["po"] == "PO-4504" and result["po_inferred"]
    assert result["po_candidates"][0]["score"] - result["po_candidates"][1]["score"] >= 0.15


def test_bank_change_is_high_severity():
    decision = run("EC-4")["decision"]
    assert decision["severity"] == "high" and decision["owner"] == "AP lead"


def test_within_tolerance_approval_carries_notes():
    decision = run("HP-2")["decision"]
    assert decision["outcome"] == "Approve"
    assert any("tolerance" in n for n in decision["notes"])


def test_split_invoice_message_explains_remaining_value():
    result = run("EC-1B")
    m03 = next(f for f in result["findings"] if f["rule"] == "M-03")
    assert "112.5%" in m03["message"] and "$15,000.00" in m03["message"]
