"""Adding vendors and POs from the app: good data goes in, bad data is refused with a readable reason,
and an invoice the agent could not verify becomes approvable once procurement adds its vendor and PO."""
from conftest import sample
from fastapi.testclient import TestClient

from app import db
from app.main import app
from app.pipeline import run_invoice

client = TestClient(app)          # no lifespan needed: these calls touch only the database

NORTHGATE = {
    "name": "Northgate Industrial Solutions LLC", "aliases": ["Northgate Industrial"], "tax_id": "83-5519024",
    "address": "700 Mill Road, Akron, OH 44308", "phone_on_file": "(330) 555-0114",
    "email": "ar@northgate.example", "bank_name": "Liberty Harbor Bank", "bank_account": "440187723309",
    "bank_routing": "021214891", "tax_rate_pct": 7.5,
}
NORTHGATE_PO = {
    "po_number": "PO-9981", "buyer": "Dana Whitfield", "description": "Safety consumables",
    "lines": [
        {"sku": "NG-GLV-NTR", "description": "Nitrile gloves, box of 100", "qty_ordered": 50, "unit_price": 11.80, "qty_received": 50},
        {"sku": "NG-TAPE-FL", "description": "Floor marking tape, yellow, 3in", "qty_ordered": 24, "unit_price": 18.40, "qty_received": 24},
        {"sku": "NG-CONE-28", "description": "Traffic cone, 28in", "qty_ordered": 12, "unit_price": 21.75, "qty_received": 12},
    ],
}


def add_vendor(**changes):
    return client.post("/api/vendors", json={**NORTHGATE, **changes})


def test_a_new_vendor_gets_the_next_id_and_its_bank_account_stays_masked():
    response = add_vendor()
    assert response.status_code == 201
    body = response.json()
    assert body["vendor_id"] == "V013" and body["bank_account"] == "...3309"
    stored = next(v for v in db.vendors() if v["vendor_id"] == "V013")
    assert stored["bank_account"] == "440187723309" and stored["expected_tax_rate"] == 0.075
    assert stored["aliases"] == "Northgate Industrial"


def test_duplicates_and_bad_details_are_refused_in_plain_words():
    assert add_vendor().status_code == 201
    again = add_vendor(name="northgate  industrial solutions llc", tax_id="")      # same vendor, other spacing
    assert again.status_code == 422 and "already exists" in again.json()["detail"]
    same_tax = add_vendor(name="Another Name Inc.", aliases=[])
    assert same_tax.status_code == 422 and "tax ID 83-5519024 already belongs to" in same_tax.json()["detail"]
    bad = add_vendor(name="Brand New Co.", aliases=[], tax_id="", bank_routing="12345", email="nope")
    assert bad.status_code == 422
    assert "routing number must be 9 digits" in bad.json()["detail"] and "email" in bad.json()["detail"]


def test_a_missing_required_field_reads_like_a_sentence():
    response = client.post("/api/vendors", json={"name": "No Bank Co."})
    assert response.status_code == 422
    assert response.json()["detail"] == "bank account: field required."


def test_purchase_orders_are_checked_before_they_go_in():
    unknown = client.post("/api/purchase_orders", json={**NORTHGATE_PO, "vendor_id": "V999"})
    assert unknown.status_code == 422 and "V999 is not in the vendor master" in unknown.json()["detail"]
    taken = client.post("/api/purchase_orders", json={**NORTHGATE_PO, "vendor_id": "V001", "po_number": "4501"})
    assert taken.status_code == 422 and "PO-4501 already exists" in taken.json()["detail"]
    over = {**NORTHGATE_PO, "vendor_id": "V001", "lines": [{**NORTHGATE_PO["lines"][0], "qty_received": 60}]}
    response = client.post("/api/purchase_orders", json=over)
    assert response.status_code == 422 and "more received (60) than ordered (50)" in response.json()["detail"]
    empty = client.post("/api/purchase_orders", json={**NORTHGATE_PO, "vendor_id": "V001", "lines": []})
    assert empty.status_code == 422


def test_a_blank_po_number_gets_the_next_one():
    response = client.post("/api/purchase_orders", json={**NORTHGATE_PO, "vendor_id": "V001", "po_number": ""})
    assert response.status_code == 201 and response.json()["po_number"] == "PO-4517"
    assert len(response.json()["lines"]) == 3 and all(l["qty_invoiced"] == 0 for l in response.json()["lines"])


def test_an_unverifiable_invoice_is_approved_once_its_vendor_and_po_are_added():
    pdf, extraction = sample("T-11")
    before = run_invoice(pdf, extraction=extraction)
    assert before["decision"]["outcome"] == "Review" and {"VM-01", "P-01"} <= set(before["decision"]["reasons"])

    vendor_id = add_vendor().json()["vendor_id"]
    assert client.post("/api/purchase_orders", json={**NORTHGATE_PO, "vendor_id": vendor_id}).status_code == 201

    pdf, extraction = sample("T-11")
    after = run_invoice(pdf, extraction=extraction)
    assert after["decision"]["outcome"] == "Approve", after["decision"]
    assert after["vendor"]["vendor_id"] == vendor_id and after["po"] == "PO-9981"
