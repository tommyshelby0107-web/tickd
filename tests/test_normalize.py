import pytest

from app.normalize import currency_code, detect_currency, invoice_key, money, po_key


def test_invoice_key_ignores_separators_and_leading_zeros():
    assert invoice_key("INV-2026-0457") == invoice_key("INV 2026 0457") == invoice_key("inv/2026/457") == "INV2026457"


def test_invoice_key_keeps_different_numbers_apart():
    assert invoice_key("INV-2026-0457") != invoice_key("INV-2026-0463")


def test_po_key_variants():
    assert po_key("PO-4501") == po_key("PO 4501") == po_key("P.O. #4501") == po_key("4501") == "PO-4501"
    assert po_key("Q3 safety order") is None


@pytest.mark.parametrize("text, expected", [
    ("TOTAL Rs 2199.00 Rs 1635.00 Rs 564.00", "INR"),     # the phone-photo receipt, as OCR read it
    ("Total ₹564.00", "INR"),
    ("Subtotal $1,194.40  Total $1,283.98", "USD"),
    ("Amount due EUR 980.00", "EUR"),
    ("Total C$ 50.00", "CAD"),                              # not USD: the $ belongs to C$
    ("Invoice 4471, 12 boxes", None),                       # no currency printed
])
def test_the_printed_currency_is_detected(text, expected):
    assert detect_currency(text) == expected


def test_model_answers_become_iso_codes():
    assert currency_code("Rs") == currency_code("₹") == currency_code("inr") == "INR"
    assert currency_code("$") == "USD" and currency_code("SGD") == "SGD" and currency_code("") is None


def test_amounts_keep_their_own_currency():
    assert money(564, "INR") == "₹564.00"                  # never shown as $564
    assert money(-206.94, "USD") == "-$206.94"
    assert money(1250, "SGD") == "SGD 1,250.00"
    assert money(10, None) == "$10.00"                      # none printed: the base currency
