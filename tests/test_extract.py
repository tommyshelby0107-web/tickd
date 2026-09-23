import pytest

from app.extract import PRINTED_PO


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
