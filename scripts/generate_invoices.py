"""Generate the sample invoice PDFs used to build and demo the invoice pipeline.

Each invoice is defined as data (build_specs), drawn with one of five vendor
layouts, and optionally degraded into an image-only "scanned" PDF. A manifest
with ground truth and the expected decision per scenario is written alongside.

Run:  python scripts/generate_invoices.py
"""
from __future__ import annotations

import csv
import json
import random
from dataclasses import dataclass, field
from datetime import date, timedelta
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path

import pymupdf
from PIL import Image, ImageDraw, ImageFilter
from reportlab.lib import colors
from reportlab.lib.pagesizes import LETTER
from reportlab.lib.units import inch
from reportlab.pdfgen import canvas

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "data"
OUT = ROOT / "samples" / "invoices"

W, H = LETTER
M = 0.75 * inch

BILL_TO = ["Meridian Industrial Supplies", "Accounts Payable", "2400 Commerce Parkway", "Columbus, OH 43219"]
SHIP_TO = ["Meridian Industrial Supplies", "Warehouse Dock 3", "2400 Commerce Parkway", "Columbus, OH 43219"]


# ---------------------------------------------------------------- data model

def q2(x) -> Decimal:
    return Decimal(x).quantize(Decimal("0.01"), ROUND_HALF_UP)


def money(x: Decimal) -> str:
    return f"-${abs(x):,.2f}" if x < 0 else f"${x:,.2f}"


def load_csv(name: str) -> list[dict]:
    with open(DATA / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


VENDORS = {v["vendor_id"]: v for v in load_csv("vendors.csv")}
PO_LINES = {(r["po_number"], r["sku"]): r for r in load_csv("po_lines.csv")}


@dataclass
class Line:
    sku: str | None
    description: str
    qty: int
    unit_price: Decimal
    printed_amount: Decimal | None = None   # set to print a wrong amount (arithmetic-error scenario)

    @property
    def amount(self) -> Decimal:
        return self.printed_amount if self.printed_amount is not None else q2(self.qty * self.unit_price)


def from_po(po: str, sku: str, qty: int | None = None, price: str | None = None,
            description: str | None = None) -> Line:
    """Build an invoice line from a PO line, optionally overriding qty, price or wording."""
    row = PO_LINES[(po, sku)]
    return Line(
        sku=sku,
        description=description or row["description"],
        qty=qty if qty is not None else int(row["qty_ordered"]),
        unit_price=Decimal(price) if price is not None else Decimal(row["unit_price"]),
    )


@dataclass
class InvoiceSpec:
    scenario: str
    title: str
    vendor_id: str
    layout: str
    invoice_number: str | None
    invoice_date: date | None
    lines: list[Line]
    po_ref: str | None = None
    po_hint: str | None = None
    tax_rate: Decimal = Decimal("0.075")
    freight: Decimal = Decimal("0")
    remit: dict | None = None          # bank details printed, if different from the vendor master
    note: str | None = None
    stamp: str | None = None
    scan: bool = False
    scan_quality: str = "normal"       # "normal" or "poor"
    number_display: str | None = None  # how the number is printed, if different from the canonical one
    vendor_info: dict | None = None    # a vendor that is NOT in the vendor master
    doc_title: str = "INVOICE"
    tax_included: bool = False         # line prices already include tax
    credit: bool = False               # credit note: amounts are printed negative
    expected: dict = field(default_factory=dict)

    @property
    def vendor(self) -> dict:
        return self.vendor_info or VENDORS[self.vendor_id]

    @property
    def sign(self) -> int:
        return -1 if self.credit else 1

    def line_amount(self, line: Line) -> Decimal:
        return line.amount * self.sign

    @property
    def number_text(self) -> str | None:
        return self.number_display or self.invoice_number

    @property
    def due_date(self) -> date | None:
        if not self.invoice_date:
            return None
        days = int(self.vendor["payment_terms"].split()[-1])
        return self.invoice_date + timedelta(days=days)

    @property
    def subtotal(self) -> Decimal:
        return sum((self.line_amount(l) for l in self.lines), Decimal("0"))

    @property
    def tax(self) -> Decimal:
        if self.tax_included:   # the tax already inside the gross line prices
            return q2(self.subtotal * self.tax_rate / (1 + self.tax_rate))
        return q2(self.subtotal * self.tax_rate)

    @property
    def total(self) -> Decimal:
        return self.subtotal + self.freight + (0 if self.tax_included else self.tax)

    @property
    def bank(self) -> dict:
        v = self.vendor
        return self.remit or {"bank_name": v["bank_name"], "routing": v["bank_routing"], "account": v["bank_account"]}

    @property
    def file_name(self) -> str:
        slug = self.vendor["name"].split()[0].lower()
        return f"{self.scenario}_{slug}_{self.invoice_number or 'no-number'}.pdf"


# ---------------------------------------------------------------- drawing helpers

def split_address(addr: str) -> list[str]:
    street, rest = addr.split(", ", 1)
    return [street, rest]


def draw_row(c: canvas.Canvas, x: float, y: float, cols, values, row_h: float) -> None:
    baseline = y - row_h + 6
    for (_, width, align), value in zip(cols, values):
        if align == "r":
            c.drawRightString(x + width - 4, baseline, value)
        elif align == "c":
            c.drawCentredString(x + width / 2, baseline, value)
        else:
            c.drawString(x + 4, baseline, value)
        x += width


def draw_table(c: canvas.Canvas, x: float, y: float, cols, rows, *, font="Helvetica", size=9, row_h=18,
               header_font="Helvetica-Bold", header_fill=None, header_color=colors.black,
               zebra=None, grid=False) -> float:
    """cols = [(header, width, align)]; rows = list of string lists. Returns y below the table."""
    total_w = sum(w for _, w, _ in cols)
    if header_fill:
        c.setFillColor(header_fill)
        c.rect(x, y - row_h, total_w, row_h, stroke=0, fill=1)
    c.setFillColor(header_color)
    c.setFont(header_font, size)
    draw_row(c, x, y, cols, [h for h, _, _ in cols], row_h)
    if grid:
        draw_grid_row(c, x, y, cols, row_h)
    elif not header_fill:
        c.setStrokeColor(colors.black)
        c.line(x, y - row_h, x + total_w, y - row_h)
    y -= row_h
    c.setFont(font, size)
    for i, row in enumerate(rows):
        if zebra and i % 2 == 1:
            c.setFillColor(zebra)
            c.rect(x, y - row_h, total_w, row_h, stroke=0, fill=1)
        c.setFillColor(colors.black)
        draw_row(c, x, y, cols, row, row_h)
        if grid:
            draw_grid_row(c, x, y, cols, row_h)
        y -= row_h
    if not grid:
        c.setStrokeColor(colors.grey)
        c.line(x, y, x + total_w, y)
    return y


def draw_grid_row(c: canvas.Canvas, x: float, y: float, cols, row_h: float) -> None:
    c.setStrokeColor(colors.HexColor("#9CA3AF"))
    for _, width, _ in cols:
        c.rect(x, y - row_h, width, row_h, stroke=1, fill=0)
        x += width


def draw_totals(c: canvas.Canvas, label_right: float, value_right: float, y: float, items,
                *, font="Helvetica", bold_font="Helvetica-Bold", size=9, step=14) -> float:
    for i, (label, value) in enumerate(items):
        c.setFont(bold_font if i == len(items) - 1 else font, size + (1 if i == len(items) - 1 else 0))
        c.drawRightString(label_right, y, label)
        c.drawRightString(value_right, y, value)
        y -= step
    return y


def totals_items(inv: InvoiceSpec, subtotal_label: str, tax_label: str, total_label: str,
                 freight_label: str = "Freight") -> list[tuple[str, str]]:
    items = [(subtotal_label, money(inv.subtotal))]
    if inv.freight:
        items.append((freight_label, money(inv.freight)))
    items.append((tax_label, money(inv.tax)))
    items.append((total_label, money(inv.total)))
    return items


def draw_note(c: canvas.Canvas, inv: InvoiceSpec, y: float, font="Helvetica-Bold", size=9) -> None:
    if not inv.note:
        return
    c.setFillColor(colors.HexColor("#FEF3C7"))
    c.rect(M, y - 8, W - 2 * M, 22, stroke=0, fill=1)
    c.setFillColor(colors.black)
    c.setFont(font, size)
    c.drawString(M + 6, y, inv.note)


def draw_stamp(c: canvas.Canvas, text: str) -> None:
    c.saveState()
    c.translate(W / 2 - 40, 290)
    c.rotate(14)
    red = colors.HexColor("#C62828")
    c.setStrokeColor(red)
    c.setFillColor(red)
    c.setLineWidth(3)
    c.setFont("Helvetica-Bold", 26)
    tw = c.stringWidth(text, "Helvetica-Bold", 26)
    c.roundRect(-tw / 2 - 14, -12, tw + 28, 42, 6, stroke=1, fill=0)
    c.drawCentredString(0, 0, text)
    c.restoreState()


def meta_rows(pairs) -> list[tuple[str, str]]:
    """Drop fields the invoice does not carry (missing number, date, PO)."""
    return [(k, v) for k, v in pairs if v]


# ---------------------------------------------------------------- five vendor layouts

def layout_classic(c: canvas.Canvas, inv: InvoiceSpec) -> None:
    """Apex Fasteners, Redline: plain corporate template."""
    v = inv.vendor
    fmt = lambda d: f"{d:%B} {d.day}, {d.year}" if d else None  # noqa: E731
    c.setFont("Helvetica-Bold", 16)
    c.drawString(M, H - M - 4, v["name"])
    c.setFont("Helvetica", 9)
    y = H - M - 20
    for line in split_address(v["address"]) + [f"Tel {v['phone_on_file']}", v["email"], f"EIN {v['tax_id']}"]:
        c.drawString(M, y, line)
        y -= 12
    c.setFont("Helvetica-Bold", 26)
    c.setFillColor(colors.HexColor("#555555"))
    c.drawRightString(W - M, H - M - 10, inv.doc_title)
    c.setFillColor(colors.black)
    my = H - M - 40
    for label, value in meta_rows([("Invoice No.", inv.number_text), ("Invoice Date", fmt(inv.invoice_date)),
                                   ("Due Date", fmt(inv.due_date)), ("PO Number", inv.po_ref),
                                   ("Terms", v["payment_terms"])]):
        c.setFont("Helvetica-Bold", 9)
        c.drawRightString(W - M - 100, my, label)
        c.setFont("Helvetica", 9)
        c.drawString(W - M - 94, my, value)
        my -= 14
    y = min(y, my) - 16
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M, y, "BILL TO")
    y -= 13
    c.setFont("Helvetica", 9)
    for line in BILL_TO:
        c.drawString(M, y, line)
        y -= 12
    cols = [("SKU", 80, "l"), ("Description", 229, "l"), ("Qty", 45, "r"), ("Unit Price", 70, "r"), ("Amount", 80, "r")]
    rows = [[l.sku, l.description, str(l.qty), money(l.unit_price), money(inv.line_amount(l))] for l in inv.lines]
    y = draw_table(c, M, y - 18, cols, rows, header_fill=colors.HexColor("#E5E7EB"))
    pct = f"{inv.tax_rate * 100:.1f}%"
    draw_totals(c, W - M - 90, W - M, y - 18, totals_items(inv, "Subtotal", f"Sales Tax ({pct})", "Total Due"))
    draw_note(c, inv, M + 110)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M, M + 70, "Remit payment by ACH to:")
    c.setFont("Helvetica", 9)
    b = inv.bank
    c.drawString(M, M + 56, f"{b['bank_name']}   ABA Routing {b['routing']}   Account {b['account']}")
    c.drawString(M, M + 30, "Thank you for your business.")


def layout_band(c: canvas.Canvas, inv: InvoiceSpec) -> None:
    """Coastal Packaging: coloured header band, bill-to / ship-to columns."""
    v = inv.vendor
    fmt = lambda d: d.strftime("%m/%d/%Y") if d else None  # noqa: E731
    teal = colors.HexColor("#0F766E")
    c.setFillColor(teal)
    c.rect(0, H - 90, W, 90, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 20)
    c.drawString(M, H - 48, v["name"])
    c.setFont("Helvetica", 9)
    c.drawString(M, H - 64, f"{v['address']}  |  {v['phone_on_file']}  |  {v['email']}")
    c.setFont("Helvetica-Bold", 22)
    c.drawRightString(W - M, H - 50, "INVOICE")
    c.setFillColor(colors.black)
    y0 = H - 120
    for x, heading, lines in [(M, "Bill To", BILL_TO), (M + 170, "Ship To", SHIP_TO)]:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(teal)
        c.drawString(x, y0, heading.upper())
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        for i, line in enumerate(lines):
            c.drawString(x, y0 - 14 - 12 * i, line)
    dx, dy = M + 340, y0
    for label, value in meta_rows([("Bill Number", inv.number_text), ("Date", fmt(inv.invoice_date)),
                                   ("Your PO", inv.po_ref), ("Terms", v["payment_terms"])]):
        c.setFont("Helvetica-Bold", 9)
        c.drawString(dx, dy, label)
        c.setFont("Helvetica", 9)
        c.drawString(dx + 64, dy, value)
        dy -= 14
    cols = [("Item", 80, "l"), ("Description", 214, "l"), ("Quantity", 60, "r"), ("Rate", 70, "r"), ("Line Total", 80, "r")]
    rows = [[l.sku, l.description, str(l.qty), money(l.unit_price), money(l.amount)] for l in inv.lines]
    y = draw_table(c, M, y0 - 80, cols, rows, header_fill=teal, header_color=colors.white,
                   zebra=colors.HexColor("#F0FDFA"))
    pct = f"{inv.tax_rate * 100:.1f}%"
    draw_totals(c, W - M - 90, W - M, y - 18, totals_items(inv, "Subtotal", f"Tax ({pct})", "Balance Due"))
    draw_note(c, inv, M + 90)
    c.setFillColor(teal)
    c.rect(0, 0, W, M + 20, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica", 9)
    b = inv.bank
    c.drawString(M, M - 10, f"Payment by wire or ACH: {b['bank_name']}  |  Routing {b['routing']}  |  Account {b['account']}")
    c.drawString(M, M - 24, "Questions about this bill? Contact our accounts team at the email above.")


def layout_compact(c: canvas.Canvas, inv: InvoiceSpec) -> None:
    """Summit Electrical: dense, monospaced, system-printed."""
    v = inv.vendor
    fmt = lambda d: d.isoformat() if d else None  # noqa: E731
    c.setFont("Courier-Bold", 14)
    c.drawString(M, H - M, v["name"].upper())
    c.setFont("Courier", 9)
    c.drawString(M, H - M - 14, v["address"])
    c.drawString(M, H - M - 26, f"Phone {v['phone_on_file']}   Fed Tax ID {v['tax_id']}")

    def dashed(y: float) -> None:
        c.setDash(3, 2)
        c.line(M, y, W - M, y)
        c.setDash()

    dashed(H - M - 36)
    c.setFont("Courier-Bold", 12)
    c.drawString(M, H - M - 54, "INVOICE")
    c.setFont("Courier", 9)
    y = H - M - 70
    fields = meta_rows([("Invoice #", inv.number_text), ("Issued", fmt(inv.invoice_date)),
                        ("Terms", v["payment_terms"]), ("Due", fmt(inv.due_date)), ("Customer PO", inv.po_ref)])
    for i in range(0, len(fields), 2):
        left = f"{fields[i][0]}: {fields[i][1]}"
        c.drawString(M, y, left)
        if i + 1 < len(fields):
            c.drawString(M + 250, y, f"{fields[i + 1][0]}: {fields[i + 1][1]}")
        y -= 12
    c.drawString(M, y - 4, "Sold to: " + ", ".join(BILL_TO[:2]))
    c.drawString(M, y - 16, "         " + ", ".join(BILL_TO[2:]))
    dashed(y - 26)
    cols = [("Qty", 50, "r"), ("Part No.", 90, "l"), ("Description", 214, "l"), ("Unit", 70, "r"), ("Ext.", 80, "r")]
    rows = [[str(l.qty), l.sku, l.description, f"{l.unit_price:,.2f}", f"{l.amount:,.2f}"] for l in inv.lines]
    y = draw_table(c, M, y - 32, cols, rows, font="Courier", header_font="Courier-Bold", size=9, row_h=16)
    pct = f"{inv.tax_rate * 100:.3f}%"
    draw_totals(c, W - M - 90, W - M, y - 16,
                totals_items(inv, "Merchandise", f"Sales tax {pct}", "AMOUNT DUE (USD)", "Freight"),
                font="Courier", bold_font="Courier-Bold")
    draw_note(c, inv, M + 90, font="Courier-Bold")
    b = inv.bank
    c.setFont("Courier", 9)
    dashed(M + 50)
    c.drawString(M, M + 34, f"Remit to: {b['bank_name']} / ABA {b['routing']} / Acct {b['account']}")
    c.drawString(M, M + 20, "Please reference the invoice number with your payment.")


def layout_letter(c: canvas.Canvas, inv: InvoiceSpec) -> None:
    """Northline Safety: letterhead style, no SKUs, reference line instead of a PO number."""
    v = inv.vendor
    fmt = lambda d: f"{d.day} {d:%b %Y}" if d else None  # noqa: E731
    c.setFont("Times-Bold", 22)
    c.drawCentredString(W / 2, H - M - 6, v["name"].upper())
    c.setFont("Times-Roman", 10)
    c.drawCentredString(W / 2, H - M - 22, v["address"])
    c.drawCentredString(W / 2, H - M - 35, f"Telephone {v['phone_on_file']}  -  {v['email']}")
    c.line(M, H - M - 45, W - M, H - M - 45)
    y = H - M - 70
    c.setFont("Times-Bold", 11)
    c.drawString(M, y, "To:")
    c.setFont("Times-Roman", 11)
    for i, line in enumerate(BILL_TO):
        c.drawString(M + 24, y - 14 * i, line)
    c.setFont("Times-Bold", 14)
    c.drawRightString(W - M, y, "INVOICE")
    c.setFont("Times-Roman", 11)
    ry = y - 18
    for label, value in meta_rows([("No.", inv.number_text), ("Dated", fmt(inv.invoice_date)),
                                   ("Order No.", inv.po_ref)]):
        c.drawRightString(W - M, ry, f"{label} {value}")
        ry -= 14
    y -= 80
    if inv.po_hint:
        c.setFont("Times-Italic", 11)
        c.drawString(M, y, inv.po_hint)
        y -= 20
    c.setFont("Times-Roman", 11)
    c.drawString(M, y, "For goods supplied as follows:")
    cols = [("Description", 270, "l"), ("Qty", 60, "r"), ("Price", 80, "r"), ("Amount", 94, "r")]
    rows = [[l.description, str(l.qty), money(l.unit_price), money(l.amount)] for l in inv.lines]
    y = draw_table(c, M, y - 10, cols, rows, font="Times-Roman", header_font="Times-Bold", size=11, row_h=20)
    items = [("Sub-total", money(inv.subtotal)), ("Sales tax", money(inv.tax)), ("TOTAL", money(inv.total))]
    y = draw_totals(c, W - M - 100, W - M, y - 20, items, font="Times-Roman", bold_font="Times-Bold", size=11, step=16)
    if inv.tax_rate == 0:
        c.setFont("Times-Italic", 10)
        c.drawString(M, y - 6, "Sales tax not collected - purchaser to self-assess use tax.")
    draw_note(c, inv, M + 120, font="Times-Bold", size=10)
    b = inv.bank
    c.setFont("Times-Roman", 11)
    c.drawString(M, M + 80, f"Kindly remit within 30 days to {b['bank_name']}, routing {b['routing']},")
    c.drawString(M, M + 66, f"account {b['account']}, quoting our invoice number.")
    c.drawString(M, M + 30, "Accounts Department")
    c.setFont("Times-Bold", 11)
    c.drawString(M, M + 16, v["name"])


def layout_grid(c: canvas.Canvas, inv: InvoiceSpec) -> None:
    """Brightpath Tools: boxed form with a payment-instructions panel."""
    v = inv.vendor
    fmt = lambda d: f"{d:%b} {d.day:02d}, {d.year}" if d else None  # noqa: E731
    navy = colors.HexColor("#1E3A5F")
    c.setFillColor(navy)
    c.rect(M, H - M - 44, 44, 44, stroke=0, fill=1)
    c.setFillColor(colors.white)
    c.setFont("Helvetica-Bold", 18)
    c.drawCentredString(M + 22, H - M - 29, "BT")
    c.setFillColor(colors.black)
    c.setFont("Helvetica-Bold", 13)
    c.drawString(M + 54, H - M - 12, v["name"])
    c.setFont("Helvetica", 9)
    for i, line in enumerate(split_address(v["address"]) + [v["phone_on_file"]]):
        c.drawString(M + 54, H - M - 26 - 11 * i, line)
    cells = [("INVOICE NUMBER", inv.number_text), ("INVOICE DATE", fmt(inv.invoice_date)), ("P.O. #", inv.po_ref),
             ("DUE DATE", fmt(inv.due_date)), ("TERMS", v["payment_terms"]), ("PAGE", "1 of 1")]
    cw, ch = 84, 30
    x0, y0 = W - M - 3 * cw, H - M
    c.setStrokeColor(navy)
    for i, (label, value) in enumerate(cells):
        cx, cy = x0 + (i % 3) * cw, y0 - (i // 3) * ch
        c.rect(cx, cy - ch, cw, ch, stroke=1, fill=0)
        c.setFont("Helvetica", 7)
        c.drawString(cx + 4, cy - 10, label)
        c.setFont("Helvetica-Bold", 9)
        c.drawString(cx + 4, cy - 24, value or "")
    sy = H - M - 90
    c.rect(M, sy - 64, 240, 64, stroke=1, fill=0)
    c.setFont("Helvetica", 7)
    c.drawString(M + 4, sy - 10, "SOLD TO")
    c.setFont("Helvetica", 9)
    for i, line in enumerate(BILL_TO):
        c.drawString(M + 4, sy - 22 - 11 * i, line)
    cols = [("#", 24, "c"), ("Item Code", 80, "l"), ("Description", 200, "l"), ("Qty", 50, "r"),
            ("Unit Price", 70, "r"), ("Total", 80, "r")]
    rows = [[str(i + 1), l.sku, l.description, str(l.qty), money(l.unit_price), money(l.amount)]
            for i, l in enumerate(inv.lines)]
    y = draw_table(c, M, sy - 84, cols, rows, header_fill=navy, header_color=colors.white, grid=True)
    pct = f"{inv.tax_rate * 100:.1f}%"
    for label, value in totals_items(inv, "SUBTOTAL", f"SALES TAX {pct}", "TOTAL DUE"):
        c.rect(W - M - 230, y - 18, 150, 18, stroke=1, fill=0)
        c.rect(W - M - 80, y - 18, 80, 18, stroke=1, fill=0)
        c.setFont("Helvetica-Bold" if label == "TOTAL DUE" else "Helvetica", 9)
        c.drawRightString(W - M - 84, y - 12, label)
        c.drawRightString(W - M - 4, y - 12, value)
        y -= 18
    py = M + 110
    c.rect(M, M + 30, W - 2 * M, 80, stroke=1, fill=0)
    c.setFont("Helvetica-Bold", 9)
    c.drawString(M + 6, py - 14, "PAYMENT INSTRUCTIONS")
    c.setFont("Helvetica", 9)
    line_y = py - 30
    if inv.note:
        c.setFont("Helvetica-Bold", 9)
        c.setFillColor(colors.HexColor("#B91C1C"))
        c.drawString(M + 6, line_y, inv.note)
        c.setFillColor(colors.black)
        c.setFont("Helvetica", 9)
        line_y -= 16
    b = inv.bank
    c.drawString(M + 6, line_y, f"Bank: {b['bank_name']}")
    c.drawString(M + 6, line_y - 13, f"Routing (ABA): {b['routing']}     Account: {b['account']}")
    c.drawString(M, M + 14, "Thank you for choosing Brightpath Tools & Supply.")


LAYOUTS = {"classic": layout_classic, "band": layout_band, "compact": layout_compact,
           "letter": layout_letter, "grid": layout_grid}


# ---------------------------------------------------------------- scan simulation

SCAN_QUALITY = {  # dpi, noise blend, speckles, blur radius
    "normal": (200, 0.07, 400, 0.6),
    "poor": (110, 0.16, 2500, 1.1),   # a fax-grade copy: low resolution, grainy, soft
}


def make_scanned(src: Path, dst: Path, *, seed: int, skew: float, quality: str = "normal") -> None:
    """Rasterise a PDF and degrade it like an office scanner: grey, skewed, noisy, no text layer."""
    dpi, noise, speckles, blur = SCAN_QUALITY[quality]
    rng = random.Random(seed)
    pages = []
    with pymupdf.open(src) as doc:
        for page in doc:
            pix = page.get_pixmap(dpi=dpi, colorspace=pymupdf.csGRAY)
            img = Image.frombytes("L", (pix.width, pix.height), pix.samples)
            img = img.rotate(skew, resample=Image.BICUBIC, fillcolor=255)
            img = Image.blend(img, Image.effect_noise(img.size, 60), noise)
            draw = ImageDraw.Draw(img)
            for _ in range(speckles):
                x, y = rng.randrange(img.width), rng.randrange(img.height)
                draw.point((x, y), fill=rng.randrange(40, 140))
            draw.rectangle((0, 0, 14, img.height), fill=200)  # scanner edge shadow
            img = img.filter(ImageFilter.GaussianBlur(blur))
            pages.append(img)
    pages[0].save(dst, "PDF", resolution=dpi, save_all=True, append_images=pages[1:])


# ---------------------------------------------------------------- scenarios

def build_specs() -> list[InvoiceSpec]:
    apex_lines = [from_po("PO-4501", s) for s in ("AF-HB-M10", "AF-NUT-M10", "AF-WSH-M10")]
    return [
        InvoiceSpec(
            scenario="HP-1", title="Happy path: clean digital invoice, exact PO match",
            vendor_id="V001", layout="classic", invoice_number="INV-2026-0457", invoice_date=date(2026, 9, 14),
            po_ref="PO-4501", lines=apex_lines,
            expected={"decision": "Approve", "rules": [], "note": "Run first in the demo; EC-2 depends on it."},
        ),
        InvoiceSpec(
            scenario="HP-2", title="Within tolerance: one price 1.2% above PO, small freight charge",
            vendor_id="V004", layout="band", invoice_number="CPK-88214", invoice_date=date(2026, 9, 16),
            po_ref="PO-4502", freight=Decimal("45.00"),
            lines=[from_po("PO-4502", "CP-BOX-18"), from_po("PO-4502", "CP-TAPE-48"),
                   from_po("PO-4502", "CP-WRAP-20", price="80.96")],
            expected={"decision": "Approve", "rules": ["M-01", "M-04", "M-05"],
                      "note": "Approved with variance notes: +$96.00 (0.76%) on subtotal, $45 freight."},
        ),
        InvoiceSpec(
            scenario="EC-1A", title="Split invoicing, first invoice (already approved on 2026-09-08)",
            vendor_id="V003", layout="compact", invoice_number="SUM-10388", invoice_date=date(2026, 9, 5),
            po_ref="PO-4503", lines=[from_po("PO-4503", "SE-LED-24", qty=250)],
            expected={"decision": "Reject", "rules": ["D-02"],
                      "note": "Already in invoice history; re-running it demonstrates duplicate detection."},
        ),
        InvoiceSpec(
            scenario="EC-1B", title="Split invoicing: second invoice pushes PO-4503 to 112.5%",
            vendor_id="V003", layout="compact", invoice_number="SUM-10421", invoice_date=date(2026, 9, 18),
            po_ref="PO-4503", lines=[from_po("PO-4503", "SE-LED-24", qty=200)],
            expected={"decision": "Review", "owner": "Buyer", "rules": ["M-02", "M-03"],
                      "note": "250 of 400 units already invoiced; only 150 remain billable."},
        ),
        InvoiceSpec(
            scenario="EC-2", title="Duplicate resubmission: HP-1 re-sent as a scan with a reformatted number",
            vendor_id="V001", layout="classic", invoice_number="INV-2026-0457", number_display="INV 2026 0457",
            invoice_date=date(2026, 9, 14), po_ref="PO-4501", lines=apex_lines,
            stamp="SECOND REQUEST", scan=True,
            expected={"decision": "Reject", "rules": ["D-02"], "depends_on": "HP-1",
                      "note": "Different file hash and number format; normalised key matches HP-1."},
        ),
        InvoiceSpec(
            scenario="EC-3", title="Scanned invoice with no PO number, only a reference line",
            vendor_id="V002", layout="letter", invoice_number="NLS-7781", invoice_date=date(2026, 9, 15),
            po_hint="Re: Q3 safety equipment order", tax_rate=Decimal("0"), scan=True,
            lines=[from_po("PO-4504", "NS-HLM-02", description="Safety helmet - Class E, white"),
                   from_po("PO-4504", "NS-GLV-L", description="Cut-resistant work gloves, large (pairs)"),
                   from_po("PO-4504", "NS-VST-XL", description="High-visibility vest, Class 2, size XL")],
            expected={"decision": "Review", "owner": "AP", "rules": ["P-04"], "suggested_po": "PO-4504",
                      "note": "PO inferred from vendor, lines and amount; never auto-approved."},
        ),
        InvoiceSpec(
            scenario="EC-4", title="Bank-detail change on an otherwise perfect invoice",
            vendor_id="V005", layout="grid", invoice_number="BTS-2291", invoice_date=date(2026, 9, 17),
            po_ref="PO-4506", lines=[from_po("PO-4506", "BT-DRL-18V"), from_po("PO-4506", "BT-BIT-SET")],
            remit={"bank_name": "Crestline Federal Bank", "routing": "322274135", "account": "773001925561"},
            note="IMPORTANT: Our banking details have changed. Please update your records and remit to the account below.",
            expected={"decision": "Review", "owner": "AP lead", "severity": "High", "rules": ["VM-03"],
                      "note": "Every commercial check passes; remit-to account differs from the vendor master."},
        ),
        InvoiceSpec(
            scenario="RV-1", title="Missing invoice number and date",
            vendor_id="V004", layout="band", invoice_number=None, invoice_date=None,
            po_ref="PO-4507", lines=[from_po("PO-4507", "CP-BOX-24")],
            expected={"decision": "Return to vendor", "rules": ["V-01"],
                      "note": "Cannot be booked or de-duplicated without a number and date."},
        ),
        InvoiceSpec(
            scenario="X-1", title="Invoice from a blocked vendor (scanned)",
            vendor_id="V006", layout="classic", invoice_number="RIS-5520", invoice_date=date(2026, 9, 12),
            po_ref="PO-4509", lines=[from_po("PO-4509", "RL-SVC-01")], scan=True,
            expected={"decision": "Reject", "rules": ["VM-02"], "note": "Vendor status is Blocked in the vendor master."},
        ),
        InvoiceSpec(
            scenario="X-2", title="Price 6% above PO, outside tolerance",
            vendor_id="V001", layout="classic", invoice_number="INV-2026-0463", invoice_date=date(2026, 9, 19),
            po_ref="PO-4508", lines=[from_po("PO-4508", "AF-ANC-12", price="44.52")],
            expected={"decision": "Review", "owner": "Buyer", "rules": ["M-01", "M-04"],
                      "note": "$2.52 per box over PO price on 60 boxes = $151.20 (6%)."},
        ),
    ]


def ground_truth(inv: InvoiceSpec) -> dict:
    b = inv.bank
    return {
        "vendor_name": inv.vendor["name"],
        "invoice_number": inv.invoice_number,
        "invoice_number_as_printed": inv.number_text,
        "invoice_date": inv.invoice_date.isoformat() if inv.invoice_date else None,
        "due_date": inv.due_date.isoformat() if inv.due_date else None,
        "po_number": inv.po_ref,
        "po_hint": inv.po_hint,
        "document_type": "credit_note" if inv.credit else "invoice",
        "lines": [{"sku": l.sku, "description": l.description, "qty": l.qty,
                   "unit_price": str(l.unit_price), "amount": str(inv.line_amount(l))} for l in inv.lines],
        "subtotal": str(inv.subtotal),
        "tax_rate": str(inv.tax_rate),
        "tax_included": inv.tax_included,
        "tax": str(inv.tax),
        "freight": str(inv.freight),
        "total": str(inv.total),
        "remit_bank": b["bank_name"],
        "remit_routing": b["routing"],
        "remit_account": b["account"],
    }


def build(specs: list[InvoiceSpec], out_dir: Path, layouts: dict | None = None, clean: bool = True) -> list[dict]:
    """Draw every spec to a PDF in out_dir (scans degraded) and return the manifest entries.
    clean=False leaves other PDFs in out_dir untouched (used to add one scenario to an existing set)."""
    layouts = {**LAYOUTS, **(layouts or {})}
    out_dir.mkdir(parents=True, exist_ok=True)
    if clean:
        for old in out_dir.glob("*.pdf"):
            old.unlink()
    manifest = []
    for i, inv in enumerate(specs):
        path = out_dir / inv.file_name
        target = path.with_suffix(".digital.pdf") if inv.scan else path
        c = canvas.Canvas(str(target), pagesize=LETTER)
        c.setTitle(f"{inv.doc_title.title()} {inv.number_text or ''}".strip())
        c.setAuthor(inv.vendor["name"])
        layouts[inv.layout](c, inv)
        if inv.stamp:
            draw_stamp(c, inv.stamp)
        c.showPage()
        c.save()
        if inv.scan:
            skew = 1.8 if inv.scan_quality == "poor" else 0.6 + 0.3 * (i % 3)
            make_scanned(target, path, seed=i, skew=skew, quality=inv.scan_quality)
            target.unlink()
        manifest.append({
            "scenario": inv.scenario,
            "title": inv.title,
            "file": inv.file_name,
            "type": ("poor scan" if inv.scan_quality == "poor" else "scanned") if inv.scan else "digital",
            "vendor_id": inv.vendor_id,
            "layout": inv.layout,
            "expected": inv.expected,
            "ground_truth": ground_truth(inv),
        })
        print(f"{inv.scenario:6} {'scan' if inv.scan else 'text':4}  {money(inv.total):>12}  {inv.file_name}")
    return manifest


def main() -> None:
    manifest = build(build_specs(), OUT)
    (OUT.parent / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(f"\n{len(manifest)} invoices written to {OUT}")


if __name__ == "__main__":
    main()
