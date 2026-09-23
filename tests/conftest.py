import sys
from datetime import date
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app import config, db  # noqa: E402
from app.extract import InvoiceData, LineItem, Sourced  # noqa: E402
from app.pipeline import sample_files  # noqa: E402
from app.text import read_pages  # noqa: E402

MANIFEST = {m["scenario"]: m for m in sample_files()}   # demo and held-out samples, keyed by scenario id


@pytest.fixture(autouse=True)
def fresh_db(tmp_path, monkeypatch):
    """Every test starts from the seed data in its own throwaway database."""
    monkeypatch.setattr(config, "STORAGE_DIR", tmp_path)
    monkeypatch.setattr(config, "DB_PATH", tmp_path / "test.db")
    monkeypatch.setattr(config, "STAGE_PAUSE_S", 0)
    db.reset()


def sample(scenario: str) -> tuple[Path, InvoiceData]:
    """The sample PDF plus a perfect extraction built from its ground truth (what an ideal LLM would return)."""
    item = MANIFEST[scenario]
    pdf = item["path"]
    text = "\n".join(p.text for p in read_pages(pdf))
    gt = item["ground_truth"]

    def src(value, quote=None):
        return Sourced(value=value, page=1 if value else None, source_quote=(quote or value) if value else None)

    printed_sku = item["layout"] not in ("letter",)     # the letter layout prints no item codes
    tax_included = gt.get("tax_included", False)
    return pdf, InvoiceData(
        document_type=gt.get("document_type", "invoice"),
        vendor_name=src(gt["vendor_name"], _find(gt["vendor_name"], text)),
        vendor_tax_id=None,
        invoice_number=src(gt["invoice_number_as_printed"]),
        invoice_date=src(gt["invoice_date"], _printed_date(gt["invoice_date"], text)),
        due_date=gt["due_date"],
        currency="USD",
        po_number=src(gt["po_number"]),
        po_hint=gt["po_hint"],
        lines=[LineItem(sku=l["sku"] if printed_sku else None, description=l["description"],
                        quantity=l["qty"], unit_price=float(l["unit_price"]), amount=float(l["amount"]))
               for l in gt["lines"]],
        subtotal=None if tax_included else float(gt["subtotal"]),
        tax_amount=float(gt["tax"]),
        tax_rate_pct=float(gt["tax_rate"]) * 100,
        tax_included_in_prices=tax_included,
        freight=float(gt["freight"]) or None,
        total=src(gt["total"], _money(float(gt["total"]))),
        remit_bank_name=gt["remit_bank"],
        remit_routing_number=src(gt["remit_routing"]),
        remit_account_number=src(gt["remit_account"]),
        notes=None,
    )


def _money(value: float) -> str:
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def _find(value: str, text: str) -> str:
    start = text.lower().find(value.lower())
    return text[start:start + len(value)] if start >= 0 else value


def _printed_date(iso: str | None, text: str) -> str | None:
    if not iso:
        return None
    d = date.fromisoformat(iso)
    for printed in (iso, f"{d:%B} {d.day}, {d.year}", d.strftime("%m/%d/%Y"), f"{d.day} {d:%b %Y}",
                    f"{d:%b} {d.day:02d}, {d.year}", f"{d:%b} {d.day}, {d.year}", f"{d.day:02d}-{d:%b}-{d.year}"):
        if printed in text:
            return printed
    return iso
