"""Adding vendors and purchase orders from the app, with the checks a vendor-master team would apply.

Bad reference data is worse than none: the rules trust it. So a new vendor needs a name and bank details, cannot
duplicate an existing vendor (by name, alias or tax ID), and a purchase order must belong to a real vendor, have a
new number and sensible lines. Anything added here is wiped by "Reset demo data", like every other change.
"""
import re
from datetime import date
from typing import Literal

from pydantic import BaseModel, Field

from . import db
from .normalize import digits, po_key


class VendorIn(BaseModel):
    name: str
    aliases: list[str] = []
    tax_id: str = ""
    status: Literal["Active", "Blocked"] = "Active"
    address: str = ""
    phone_on_file: str = ""
    email: str = ""
    bank_name: str = ""
    bank_account: str
    bank_routing: str = ""
    tax_rate_pct: float = Field(0.0, ge=0, le=30)
    payment_terms: str = "Net 30"


class POLineIn(BaseModel):
    sku: str = ""
    description: str
    qty_ordered: float = Field(gt=0)
    unit_price: float = Field(gt=0)
    qty_received: float = Field(0, ge=0)


class PurchaseOrderIn(BaseModel):
    vendor_id: str
    po_number: str = ""
    buyer: str = ""
    description: str = ""
    status: Literal["Open", "Closed"] = "Open"
    lines: list[POLineIn] = Field(min_length=1)


class RefDataError(ValueError):
    """The input was understood but breaks a rule; the message says which, in plain words."""


def _key(name: str) -> str:
    return re.sub(r"[^a-z0-9]", "", name.lower())


def add_vendor(v: VendorIn) -> dict:
    name = " ".join(v.name.split())
    aliases = [" ".join(a.split()) for a in v.aliases if a.strip()]
    problems = []
    if len(name) < 2:
        problems.append("the vendor name is required")
    account = digits(v.bank_account)
    if not 4 <= len(account) <= 17:
        problems.append("the bank account must be 4 to 17 digits")
    if v.bank_routing and len(digits(v.bank_routing)) != 9:
        problems.append("the routing number must be 9 digits")
    if v.email and not re.fullmatch(r"[^@\s]+@[^@\s]+\.[^@\s]+", v.email.strip()):
        problems.append("the email address does not look right")
    for existing in db.vendors():
        known = {_key(existing["name"]), *(_key(a) for a in (existing["aliases"] or "").split("|") if a)}
        if {_key(name), *(_key(a) for a in aliases)} & known:
            problems.append(f"{existing['name']} ({existing['vendor_id']}) already exists with that name")
        if v.tax_id and digits(v.tax_id) and digits(v.tax_id) == digits(existing["tax_id"]):
            problems.append(f"tax ID {v.tax_id} already belongs to {existing['name']} ({existing['vendor_id']})")
    if problems:
        raise RefDataError("Can't add this vendor: " + "; ".join(dict.fromkeys(problems)) + ".")
    return db.add_vendor({
        "name": name, "aliases": "|".join(aliases), "tax_id": v.tax_id.strip(), "status": v.status,
        "address": v.address.strip(), "phone_on_file": v.phone_on_file.strip(), "email": v.email.strip().lower(),
        "bank_name": v.bank_name.strip(), "bank_account": account, "bank_routing": digits(v.bank_routing),
        "expected_tax_rate": round(v.tax_rate_pct / 100, 5), "payment_terms": v.payment_terms.strip() or "Net 30",
    })


def add_purchase_order(po: PurchaseOrderIn) -> dict:
    problems = []
    vendor = next((v for v in db.vendors() if v["vendor_id"] == po.vendor_id), None)
    if not vendor:
        problems.append(f"vendor {po.vendor_id} is not in the vendor master")
    number = po_key(po.po_number) if po.po_number.strip() else db.next_po_number()
    if not number:
        problems.append(f"'{po.po_number}' is not a PO number (use something like PO-4520)")
    elif db.purchase_order(number):
        problems.append(f"{number} already exists")
    skus = [l.sku.strip().upper() for l in po.lines if l.sku.strip()]
    if len(skus) != len(set(skus)):
        problems.append("each SKU can appear only once on a PO")
    for i, line in enumerate(po.lines, 1):
        if not line.description.strip():
            problems.append(f"line {i} needs a description")
        if line.qty_received > line.qty_ordered:
            problems.append(f"line {i}: more received ({line.qty_received:g}) than ordered ({line.qty_ordered:g})")
    if problems:
        raise RefDataError("Can't add this PO: " + "; ".join(problems) + ".")
    lines = [{"sku": l.sku.strip().upper(), "description": " ".join(l.description.split()),
              "qty_ordered": l.qty_ordered, "unit_price": round(l.unit_price, 4), "qty_received": l.qty_received}
             for l in po.lines]
    return db.add_purchase_order({"po_number": number, "vendor_id": po.vendor_id, "status": po.status,
                                  "created_date": date.today().isoformat(), "buyer": " ".join(po.buyer.split()),
                                  "description": " ".join(po.description.split())}, lines)
