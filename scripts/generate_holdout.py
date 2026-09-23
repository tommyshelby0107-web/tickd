"""Generate the held-out test set: new vendors, new layouts and scenarios the system was never tuned on.

The demo set (samples/invoices) was used while building the rules. This set is only for testing, so its
results show how the system copes with invoices it has not seen - the question an interviewer will ask.

Run:  python scripts/generate_holdout.py
"""
import json
import sys
from datetime import date, timedelta
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors

sys.path.insert(0, str(Path(__file__).resolve().parent))
import generate_invoices as g  # noqa: E402  (reuse data model, drawing helpers and scan simulation)
from generate_invoices import BILL_TO, H, M, SHIP_TO, W, InvoiceSpec, Line, from_po, money  # noqa: E402

OUT = g.ROOT / "samples" / "holdout" / "invoices"

PINNACLE = {  # not in the vendor master on purpose
    "vendor_id": None, "name": "Pinnacle Office Supply", "address": "77 Commerce Street, Dayton, OH 45402",
    "phone_on_file": "(937) 555-0199", "email": "billing@pinnacleoffice.example", "tax_id": "81-5530927",
    "payment_terms": "Net 30", "bank_name": "Gem City Bank", "bank_routing": "042000314", "bank_account": "118830045529",
}


def usd(d: date | None, style: str) -> str | None:
    if not d:
        return None
    return {"short": f"{d:%b} {d.day}, {d.year}", "ledger": f"{d.day:02d}-{d:%b}-{d.year}",
            "long": f"{d:%B} {d.day}, {d.year}"}[style]


def pay_line(inv: InvoiceSpec) -> str:
    b = inv.bank
    return f"{b['bank_name']}  ·  Routing {b['routing']}  ·  Account {b['account']}"


def totals(inv: InvoiceSpec) -> list[tuple[str, str]]:
    pct = f"{inv.tax_rate * 100:.1f}%"
    if inv.tax_included:
        return [(f"Total (includes {pct} sales tax of {money(inv.tax)})", money(inv.total))]
    items = [("Subtotal", money(inv.subtotal))]
    if inv.freight:
        items.append(("Shipping", money(inv.freight)))
    items += [(f"Sales tax ({pct})", money(inv.tax)), ("Amount due", money(inv.total))]
    return items


# ---------------------------------------------------------------- layout 6: minimal (modern SaaS style)

def layout_minimal(c, inv: InvoiceSpec) -> None:
    v = inv.vendor
    ink, soft = colors.HexColor("#1A1F36"), colors.HexColor("#697386")
    c.setFillColor(ink)
    c.setFont("Helvetica-Bold", 24)
    c.drawString(M, H - M - 10, inv.doc_title.title())
    c.setFont("Helvetica-Bold", 11)
    c.drawRightString(W - M, H - M - 2, v["name"])
    c.setFont("Helvetica", 9)
    c.setFillColor(soft)
    for i, line in enumerate(g.split_address(v["address"]) + [v["email"]]):
        c.drawRightString(W - M, H - M - 16 - 12 * i, line)
    y = H - M - 50
    for label, value in g.meta_rows([("Invoice number", inv.number_text), ("Date of issue", usd(inv.invoice_date, "short")),
                                     ("Date due", usd(inv.due_date, "short")), ("Purchase order", inv.po_ref)]):
        c.setFillColor(soft)
        c.setFont("Helvetica", 9)
        c.drawString(M, y, label)
        c.setFillColor(ink)
        c.drawString(M + 95, y, value)
        y -= 14
    c.setFont("Helvetica-Bold", 16)
    due = f" due {usd(inv.due_date, 'short')}" if inv.due_date else ""
    c.drawString(M, y - 14, f"{money(inv.total)} USD{due}")
    y -= 44
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M, y, "Bill to")
    c.setFont("Helvetica", 9)
    for i, line in enumerate(BILL_TO):
        c.drawString(M, y - 13 - 12 * i, line)
    cols = [("Item #", 80, "l"), ("Description", 234, "l"), ("Qty", 50, "r"), ("Unit price", 70, "r"), ("Amount", 70, "r")]
    rows = [[l.sku or "", l.description, str(l.qty), money(l.unit_price), money(inv.line_amount(l))] for l in inv.lines]
    y = g.draw_table(c, M, y - 76, cols, rows, row_h=20)
    g.draw_totals(c, W - M - 90, W - M, y - 20, totals(inv))
    g.draw_note(c, inv, M + 80)
    c.setFillColor(soft)
    c.setFont("Helvetica", 8.5)
    c.drawString(M, M + 40, "Pay by ACH or wire")
    c.setFillColor(ink)
    c.drawString(M, M + 27, pay_line(inv))


# ---------------------------------------------------------------- layout 7: ledger (paginated)

LEDGER_ROWS_FIRST, LEDGER_ROWS_NEXT = 16, 24


def layout_ledger(c, inv: InvoiceSpec) -> None:
    rows = [[str(i + 1), l.sku or "", l.description, str(l.qty), f"{l.unit_price:,.2f}", f"{inv.line_amount(l):,.2f}"]
            for i, l in enumerate(inv.lines)]
    chunks = [rows[:LEDGER_ROWS_FIRST]]
    rest = rows[LEDGER_ROWS_FIRST:]
    while rest:
        chunks.append(rest[:LEDGER_ROWS_NEXT])
        rest = rest[LEDGER_ROWS_NEXT:]
    cols = [("Ln", 26, "r"), ("Item", 82, "l"), ("Description", 216, "l"), ("Qty", 44, "r"), ("Price", 66, "r"),
            ("Extension", 70, "r")]
    green = colors.HexColor("#14532D")
    for page, chunk in enumerate(chunks, start=1):
        v = inv.vendor
        c.setFillColor(colors.HexColor("#F1F5F2"))
        c.rect(0, H - 86, W, 86, stroke=0, fill=1)
        c.setFillColor(green)
        c.rect(0, H - 86, 6, 86, stroke=0, fill=1)
        c.setFont("Helvetica-Bold", 15)
        c.drawString(M, H - 40, v["name"].upper())
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 8.5)
        c.drawString(M, H - 55, f"{v['address']}  ·  {v['phone_on_file']}")
        c.drawString(M, H - 67, f"Federal tax ID {v['tax_id']}")
        c.setFont("Helvetica-Bold", 12)
        c.drawRightString(W - M, H - 38, inv.doc_title)
        c.setFont("Helvetica", 8.5)
        meta = g.meta_rows([("Invoice #", inv.number_text), ("Date", usd(inv.invoice_date, "ledger")),
                            ("Customer PO", inv.po_ref), ("Account", "MER-1042"), ("Page", f"{page} of {len(chunks)}")])
        for i, (label, value) in enumerate(meta):
            c.drawRightString(W - M - 70, H - 52 - 10 * i, label)
            c.drawString(W - M - 64, H - 52 - 10 * i, value)
        y = H - 110
        if page == 1:
            for x, heading, lines in [(M, "BILL TO", BILL_TO), (M + 250, "SHIP TO", SHIP_TO)]:
                c.setFont("Helvetica-Bold", 8.5)
                c.drawString(x, y, heading)
                c.setFont("Helvetica", 8.5)
                for i, line in enumerate(lines):
                    c.drawString(x, y - 12 - 11 * i, line)
            y -= 66
        y = g.draw_table(c, M, y, cols, chunk, size=8.5, row_h=17, header_fill=colors.HexColor("#DCE7DF"))
        if page < len(chunks):
            c.setFont("Helvetica-Oblique", 8.5)
            c.drawRightString(W - M, y - 16, f"Continued on page {page + 1}")
            c.showPage()
            continue
        items = [("Merchandise total", money(inv.subtotal))]
        if inv.freight:
            items.append(("Freight", money(inv.freight)))
        items += [(f"Sales tax {inv.tax_rate * 100:.2f}%", money(inv.tax)), ("INVOICE TOTAL", money(inv.total))]
        g.draw_totals(c, W - M - 90, W - M, y - 18, items, size=9)
        g.draw_note(c, inv, M + 70)
        c.setFont("Helvetica", 8.5)
        c.drawString(M, M + 36, "Remittance: " + pay_line(inv))
        c.drawString(M, M + 24, f"Terms {v['payment_terms']}. Please quote the invoice number with payment.")


# ---------------------------------------------------------------- layout 8: service invoice

def layout_service(c, inv: InvoiceSpec) -> None:
    v = inv.vendor
    purple = colors.HexColor("#4C1D95")
    c.setFillColor(purple)
    c.setFont("Helvetica-Bold", 18)
    c.drawString(M, H - M - 6, v["name"])
    c.setFillColor(colors.black)
    c.setFont("Helvetica", 9)
    c.drawString(M, H - M - 20, f"{v['address']}  |  {v['phone_on_file']}")
    c.setFont("Helvetica-Bold", 13)
    c.drawRightString(W - M, H - M - 6, "SERVICE INVOICE")
    y = H - M - 50
    start = inv.invoice_date - timedelta(days=11) if inv.invoice_date else None
    period = f"{usd(start, 'short')} - {usd(inv.invoice_date, 'short')}" if start else None
    for label, value in g.meta_rows([("Invoice No.", inv.number_text), ("Invoice Date", usd(inv.invoice_date, "long")),
                                     ("Service period", period), ("Work order / PO", inv.po_ref),
                                     ("Terms", v["payment_terms"])]):
        c.setFont("Helvetica-Bold", 9)
        c.drawString(W - M - 230, y, label)
        c.setFont("Helvetica", 9)
        c.drawString(W - M - 130, y, value)
        y -= 13
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M, H - M - 50, "Customer")
    c.setFont("Helvetica", 9)
    for i, line in enumerate(BILL_TO):
        c.drawString(M, H - M - 63 - 12 * i, line)
    y = H - M - 150
    c.setFont("Helvetica-Bold", 10)
    c.drawString(M, y, "Description of work")
    c.setFont("Helvetica", 9)
    for i, line in enumerate(["Quarterly preventive maintenance of rooftop HVAC units 1-4 at the Meridian warehouse:",
                              "filters replaced on all units, coils inspected, old filters removed and disposed of."]):
        c.drawString(M, y - 14 - 12 * i, line)
    cols = [("Description", 314, "l"), ("Qty", 50, "r"), ("Rate", 70, "r"), ("Amount", 70, "r")]
    rows = [[l.description, str(l.qty), money(l.unit_price), money(inv.line_amount(l))] for l in inv.lines]
    y = g.draw_table(c, M, y - 50, cols, rows, row_h=20, header_fill=colors.HexColor("#EDE9FE"))
    g.draw_totals(c, W - M - 90, W - M, y - 20, totals(inv))
    c.setFont("Helvetica", 9)
    c.drawString(M, M + 50, "Please remit to: " + pay_line(inv))
    c.drawString(M, M + 36, "Thank you for trusting us with your facility.")


HOLDOUT_LAYOUTS = {"minimal": layout_minimal, "ledger": layout_ledger, "service": layout_service}


# ---------------------------------------------------------------- scenarios

def holdout_specs() -> list[InvoiceSpec]:
    harborline = [from_po("PO-4511", row["sku"]) for row in g.load_csv("po_lines.csv") if row["po_number"] == "PO-4511"]
    return [
        InvoiceSpec(
            scenario="T-01", title="Prices include sales tax (tax-inclusive invoice)",
            vendor_id="V007", layout="minimal", invoice_number="KIT-22817", invoice_date=date(2026, 9, 15),
            po_ref="PO-4510", tax_included=True,
            lines=[from_po("PO-4510", "KT-IMP-12", price="202.10"), from_po("PO-4510", "KT-SOC-40", price="77.40")],
            expected={"decision": "Approve", "rules": [],
                      "note": "Gross prices are PO price + 7.5% tax; net of tax they match the PO exactly."},
        ),
        InvoiceSpec(
            scenario="T-02", title="Two-page invoice with 28 lines",
            vendor_id="V008", layout="ledger", invoice_number="HOP-500931", invoice_date=date(2026, 9, 10),
            po_ref="PO-4511", lines=harborline,
            expected={"decision": "Approve", "rules": [], "note": "Lines continue onto page 2; totals are on page 2."},
        ),
        InvoiceSpec(
            scenario="T-03", title="Bundled lump-sum line instead of the PO's three lines",
            vendor_id="V009", layout="service", invoice_number="CFS-2026-118", invoice_date=date(2026, 9, 12),
            po_ref="PO-4512",
            lines=[Line(None, "Quarterly HVAC service - labour, filters and disposal (lump sum)", 1, Decimal("2025.00"))],
            expected={"decision": "Review", "owner": "Buyer", "rules_any": ["M-00", "M-01"],
                      "note": "Same total as the PO, but the lines cannot be matched one to one."},
        ),
        InvoiceSpec(
            scenario="T-04", title="Invoice against a closed, fully billed PO",
            vendor_id="V001", layout="classic", invoice_number="INV-2026-0512", invoice_date=date(2026, 9, 16),
            po_ref="PO-4480", lines=[from_po("PO-4480", "AF-SCR-8")],
            expected={"decision": "Review", "owner": "Buyer", "rules": ["P-03"],
                      "note": "PO-4480 is Closed and already 100% invoiced."},
        ),
        InvoiceSpec(
            scenario="T-05", title="Billed for goods not yet received",
            vendor_id="V010", layout="minimal", invoice_number="DPC-77120", invoice_date=date(2026, 9, 17),
            po_ref="PO-4513", lines=[from_po("PO-4513", "DP-PAL-4840")],
            expected={"decision": "Review", "owner": "Warehouse", "rules": ["M-02"],
                      "note": "300 pallets billed; only 180 received so far."},
        ),
        InvoiceSpec(
            scenario="T-06", title="Arithmetic error on a line (typed 609.00 instead of 690.00)",
            vendor_id="V011", layout="ledger", invoice_number="ECS-40218", invoice_date=date(2026, 9, 11),
            po_ref="PO-4514",
            lines=[from_po("PO-4514", "EG-DEG-5"),
                   Line("EG-ABS-25", "Absorbent granules, 25 lb bag", 40, Decimal("17.25"), printed_amount=Decimal("609.00"))],
            expected={"decision": "Review", "owner": "AP", "rules": ["V-02"],
                      "note": "40 x 17.25 = 690.00, but the line says 609.00; the totals follow the wrong figure."},
        ),
        InvoiceSpec(
            scenario="T-07", title="Same vendor, same amount, new number, 13 days after a paid invoice",
            vendor_id="V004", layout="band", invoice_number="CPK-88302", invoice_date=date(2026, 9, 2),
            po_ref="PO-4515", lines=[from_po("PO-4515", "CP-BOX-18")],
            expected={"decision": "Review", "owner": "AP", "rules": ["D-03"],
                      "note": "Matches paid invoice CPK-88120 ($3,878.60, 2026-08-20) on amount; could be a re-bill."},
        ),
        InvoiceSpec(
            scenario="T-08", title="Vendor not in the vendor master (scanned)",
            vendor_id="", vendor_info=PINNACLE, layout="minimal", invoice_number="POS-3391",
            invoice_date=date(2026, 9, 18), scan=True,
            lines=[Line("PN-CHR-M", "Ergonomic office chair, mesh", 4, Decimal("219.00")),
                   Line("PN-ARM-2", "Monitor arm, dual", 4, Decimal("64.50"))],
            expected={"decision": "Review", "owner": "Procurement", "rules": ["VM-01"],
                      "note": "Unknown vendor and no PO: must not be paid until onboarded."},
        ),
        InvoiceSpec(
            scenario="T-09", title="Poor-quality scan (fax-grade) of a clean invoice",
            vendor_id="V012", layout="minimal", invoice_number="LBS-10442", invoice_date=date(2026, 9, 19),
            po_ref="PO-4516", scan=True, scan_quality="poor",
            lines=[from_po("PO-4516", "LB-6205"), from_po("PO-4516", "LB-SEAL-35")],
            expected={"decision": "Approve", "acceptable": ["Review"], "acceptable_rules": ["V-05"],
                      "note": "Approve if read correctly; a low-confidence review (V-05) is also safe. Approving wrong values is not."},
        ),
        InvoiceSpec(
            scenario="T-10", title="Credit note for returned goods",
            vendor_id="V001", layout="classic", invoice_number="CN-2026-0031", invoice_date=date(2026, 9, 20),
            po_ref="PO-4501", doc_title="CREDIT NOTE", credit=True,
            lines=[from_po("PO-4501", "AF-HB-M10", qty=5, description="Returned: hex bolt M10 x 50, box of 100")],
            note="Credit against invoice INV-2026-0457 - 5 boxes returned damaged.",
            expected={"decision": "Review", "owner": "AP", "rules": ["V-06"],
                      "note": "A credit note is not a bill to pay; it must be applied against the vendor balance."},
        ),
    ]


def main() -> None:
    manifest = g.build(holdout_specs(), OUT, HOLDOUT_LAYOUTS)
    for item in manifest:
        item["set"] = "holdout"
    (OUT.parent / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{len(manifest)} held-out invoices written to {OUT}")


if __name__ == "__main__":
    main()
