"""The Python fast path may decline an invoice, but when it accepts one, every field must be right."""
import pytest
from conftest import MANIFEST

from app.parser import parse_invoice
from app.text import PageText, read_pages

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from check_extraction import score  # noqa: E402

PAGES = {s: read_pages(item["path"]) for s, item in MANIFEST.items()}


@pytest.mark.parametrize("scenario", sorted(MANIFEST))
def test_accepted_readings_are_exactly_right(scenario):
    data, reasons = parse_invoice(PAGES[scenario])
    if data is None:
        assert reasons, "a declined invoice must say why"
        return
    checks = score(data.model_dump(), MANIFEST[scenario]["ground_truth"])
    assert all(checks.values()), f"parser accepted {scenario} with wrong fields: {[k for k, v in checks.items() if not v]}"


def test_parser_handles_most_clean_invoices():
    accepted = [s for s in MANIFEST if parse_invoice(PAGES[s])[0] is not None]
    assert len(accepted) >= 12, accepted


@pytest.mark.parametrize("scenario, reason", [
    ("RV-1", "invoice number not found"),                 # nothing to read: the AI (and then V-01) handle it
    ("T-06", "qty x price is not the amount"),            # a real arithmetic error on the invoice
    ("T-08", "vendor not found"),                          # unknown vendor
    ("T-11", "vendor not found"),
])
def test_declines_what_it_cannot_prove(scenario, reason):
    data, reasons = parse_invoice(PAGES[scenario])
    assert data is None and any(reason in r for r in reasons), reasons


def test_a_missing_line_is_caught_by_the_totals():
    page = PAGES["HP-1"][0]
    text = "\n".join(l for l in page.text.splitlines() if not l.startswith("AF-NUT-M10"))
    data, reasons = parse_invoice([PageText(page.number, text, page.source)])
    assert data is None and any("subtotal" in r for r in reasons), reasons


def test_two_different_invoice_numbers_are_ambiguous():
    page = PAGES["HP-1"][0]
    data, reasons = parse_invoice([PageText(page.number, page.text + "\nInvoice No. INV-2026-9999", page.source)])
    assert data is None and any("more than one invoice number" in r for r in reasons), reasons
