"""Invoices keep their own currency: never converted, and never compared with a PO kept in another currency."""
from conftest import sample
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline import run_invoice


def run_in_rupees() -> dict:
    pdf, extraction = sample("HP-1")          # a clean invoice that normally approves
    extraction.currency = "INR"               # the same figures, printed in rupees
    return run_invoice(pdf, extraction=extraction)


def test_an_invoice_in_another_currency_is_held_not_approved():
    result = run_in_rupees()
    assert result["decision"]["outcome"] == "Review" and "V-07" in result["decision"]["reasons"]
    v07 = next(f for f in result["findings"] if f["rule"] == "V-07")
    assert "₹2,588.06" in v07["message"] and "not converted" in v07["message"]
    assert result["invoice"]["currency"] == "INR"


def test_rupees_are_never_compared_with_a_dollar_po():
    rules = {f["rule"] for f in run_in_rupees()["findings"]}
    assert not {"M-01", "M-03", "M-04"} & rules            # price and PO-total checks skipped, not "passed"


def test_a_person_cannot_approve_it_against_the_dollar_po():
    result = run_in_rupees()
    response = TestClient(app).post(f"/api/runs/{result['run_id']}/review",
                                    json={"action": "approve", "reason": "looks fine"})
    assert response.status_code == 409 and "currency" in response.json()["detail"]


def test_an_invoice_in_our_currency_still_approves():
    pdf, extraction = sample("HP-1")
    result = run_invoice(pdf, extraction=extraction)
    assert result["decision"]["outcome"] == "Approve" and "$2,588.06" in result["decision"]["summary"]
