from pathlib import Path

import pytest

from app import extract
from app.extract import (PRINTED_PO, ExtractionError, InvoiceData, LineItem, _infer_tax_included,
                         _recover_printed_total, _strip_number_label)
from app.text import PageText


@pytest.mark.parametrize("text, expected", [
    ("Your PO PO-4507", "PO-4507"),
    ("PO Number PO-4501", "PO-4501"),
    ("Customer PO: PO-4503", "PO-4503"),
    ("P.O. # PO-4506", "PO-4506"),
    ("P.O. 4506", "4506"),
])
def test_printed_po_is_recovered(text, expected):
    assert PRINTED_PO.search(text).group(1) == expected


@pytest.mark.parametrize("text", ["Re: Q3 safety equipment order", "Invoice No. INV-2026-0457", "Postal code 43219"])
def test_wording_without_a_po_number_is_not_turned_into_one(text):
    assert PRINTED_PO.search(text) is None


@pytest.mark.parametrize("quote, expected", [
    ("TOTAL $5,565.00", "5565.00"),
    ("Total Due -$206.94", "-206.94"),
    ("Balance Due $13,650.20", "13650.20"),
    ("Total", None),                       # no amount in the quote: nothing is invented
])
def test_total_is_recovered_only_from_a_printed_amount(quote, expected):
    data = invoice(total={"value": None, "page": 1, "source_quote": quote})
    _recover_printed_total(data)
    assert data.total.value == expected


def invoice(**fields) -> InvoiceData:
    empty = {"value": None, "page": None, "source_quote": None}
    base = dict(vendor_name=empty, vendor_tax_id=None, invoice_number=empty, invoice_date=empty, due_date=empty,
                currency=None, po_number=empty, po_hint=None, lines=[], subtotal=None, tax_amount=None,
                tax_rate_pct=None, tax_included_in_prices=False, freight=None, total=empty, remit_bank_name=None,
                remit_routing_number=empty, remit_account_number=empty, notes=None)
    return InvoiceData(**{**base, **fields})


LINES = [LineItem(sku="A", description="a", quantity=6, unit_price=202.10, amount=1212.60),
         LineItem(sku="B", description="b", quantity=10, unit_price=77.40, amount=774.00)]


def test_tax_included_is_inferred_when_lines_already_add_up_to_the_total():
    data = invoice(lines=LINES, tax_amount=138.60, total="1986.60")
    _infer_tax_included(data)
    assert data.tax_included_in_prices


@pytest.mark.parametrize("read, expected", [
    ("Accounts Payable No. NLS-7781", "NLS-7781"),     # OCR merged the address column into the number
    ("Invoice # SUM-10421", "SUM-10421"),
    ("INV 2026 0457", "INV 2026 0457"),               # no label: a spaced number is left exactly as printed
    ("INV-2026-0457", "INV-2026-0457"),
])
def test_label_words_are_stripped_from_the_invoice_number(read, expected):
    data = invoice(invoice_number={"value": read, "page": 1, "source_quote": read})
    _strip_number_label(data)
    assert data.invoice_number.value == expected


def test_tax_on_top_is_left_alone():
    data = invoice(lines=LINES, tax_amount=148.99, total="2135.59")      # 1986.60 + 148.99: tax added on top
    _infer_tax_included(data)
    assert not data.tax_included_in_prices


# ---------------------------------------------------------------- which reader gets a phone photo

PHOTO = [PageText(1, "blurry text", "ocr", 42.0)]        # OCR confidence far below 70: the page goes as an image


def readers(monkeypatch, gemini, mistral):
    calls = []

    def fake(name, outcome):
        def read(prompt, pdf_path, image_pages, skipped):
            calls.append((name, image_pages))
            if outcome == "busy":
                skipped.append(f"{name}: busy (503)")
                raise ExtractionError(f"{name} unavailable")
            return invoice(), name, 0, 0
        return read

    monkeypatch.setattr(extract, "PROVIDER_ORDER", ["groq", "gemini", "mistral"])
    for name, outcome in (("groq", "reads"), ("gemini", gemini), ("mistral", mistral)):
        monkeypatch.setattr(extract, f"{name.upper()}_API_KEY", "key")
        monkeypatch.setattr(extract, f"_{name}", fake(name, outcome))
    return calls


def test_a_photo_goes_to_mistral_when_gemini_is_busy(monkeypatch):
    calls = readers(monkeypatch, gemini="busy", mistral="reads")
    result = extract.extract_invoice(Path("photo.pdf"), PHOTO)
    assert calls == [("gemini", [1]), ("mistral", [1])]           # never Qwen: it cannot see images
    assert result.model == "mistral" and result.image_pages == [1]
    assert "gemini: busy (503)" in result.fallbacks


def test_every_reason_is_kept_when_no_reader_is_free(monkeypatch):
    readers(monkeypatch, gemini="busy", mistral="busy")
    with pytest.raises(ExtractionError) as failure:
        extract.extract_invoice(Path("photo.pdf"), PHOTO)
    assert "gemini: busy (503)" in str(failure.value) and "mistral: busy (503)" in str(failure.value)
