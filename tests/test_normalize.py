from app.normalize import invoice_key, po_key


def test_invoice_key_ignores_separators_and_leading_zeros():
    assert invoice_key("INV-2026-0457") == invoice_key("INV 2026 0457") == invoice_key("inv/2026/457") == "INV2026457"


def test_invoice_key_keeps_different_numbers_apart():
    assert invoice_key("INV-2026-0457") != invoice_key("INV-2026-0463")


def test_po_key_variants():
    assert po_key("PO-4501") == po_key("PO 4501") == po_key("P.O. #4501") == po_key("4501") == "PO-4501"
    assert po_key("Q3 safety order") is None
