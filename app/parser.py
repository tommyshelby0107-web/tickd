"""Fast path: read an invoice with plain Python, no AI.

Python reads the text of a digital PDF perfectly; the hard part is knowing which number is which across vendor
layouts. So this parser only returns a result when it can PROVE it:
  - the vendor is found in the vendor master,
  - the invoice number, date and total are each found exactly once,
  - every line reconciles (qty x price = amount), and the lines add up to the subtotal and the total.
Anything else returns the reasons, and the invoice goes to the AI instead.
"""
import re
from datetime import datetime

from . import db
from .normalize import invoice_key, po_key
from .schema import InvoiceData, LineItem, Sourced
from .text import PageText

TOLERANCE = 0.01
MONEY = r"-?\$?\s?-?\d[\d,]*\.\d{2}"
AMOUNT = re.compile(r"(-?)\$?\s?(-?)(\d[\d,]*\.\d{2})")

# Line items: "[#] [SKU] description qty price amount", or (system-printed) "qty SKU description price amount"
LINE_AMOUNTS_LAST = re.compile(
    rf"^(?:\d{{1,3}}\s+)?(?P<body>.+?)\s+(?P<qty>\d+(?:\.\d+)?)\s+(?P<price>{MONEY})\s+(?P<amount>{MONEY})$")
LINE_QTY_FIRST = re.compile(rf"^(?P<qty>\d+(?:\.\d+)?)\s+(?P<body>.+?)\s+(?P<price>{MONEY})\s+(?P<amount>{MONEY})$")
SKU = re.compile(r"^([A-Z0-9]{2,}(?:-[A-Z0-9]+)+)\s+(.+)$")

DATE = r"(\d{4}-\d{2}-\d{2}|\d{1,2}/\d{1,2}/\d{4}|\d{1,2}-[A-Za-z]{3}-\d{4}|[A-Za-z]{3,9}\.? \d{1,2}, \d{4}|\d{1,2} [A-Za-z]{3,9}\.? \d{4})"
DATE_FORMATS = ("%Y-%m-%d", "%m/%d/%Y", "%d-%b-%Y", "%B %d, %Y", "%b %d, %Y", "%d %B %Y", "%d %b %Y")

INVOICE_NUMBER = [
    re.compile(r"\b(?:invoice\s*(?:no\.?|number|#)|bill\s*(?:no\.?|number)|document\s*no\.?)\s*[:#]?\s*"
               r"(?P<v>[A-Z0-9][A-Z0-9\-/]*(?:\s\d{2,}){0,2})", re.IGNORECASE),
    re.compile(r"(?:^|\s)(?<!Order )No\.\s*(?P<v>[A-Z]{2,}[A-Z0-9\-/]*\d[A-Z0-9\-/]*)"),   # letter style "No. NLS-7781"
]
INVOICE_DATE = re.compile(rf"\b(?:invoice date|date of issue|issued|dated|(?<!due )date)\s*:?\s*{DATE}", re.IGNORECASE)
DUE_DATE = re.compile(rf"\b(?:due date|date due|due)\s*:?\s*{DATE}", re.IGNORECASE)
PO_NUMBER = re.compile(r"\bP\.?O\.?[\s#:-]*(\d{3,})\b", re.IGNORECASE)
PO_LABEL = re.compile(r"\b(?:P\.?O\.?(?:\s*(?:#|number|no\.?))?|purchase order|customer po|your po|order no\.?)(?=\W|$)",
                      re.IGNORECASE)
ROUTING = re.compile(r"\b(?:routing(?:\s*\(aba\))?|aba(?:\s*routing)?)\s*[:#]?\s*(\d{9})\b", re.IGNORECASE)
ACCOUNT = re.compile(r"\b(?:account|acct)\b\.?\s*[:#]?\s*(\d{6,17})\b", re.IGNORECASE)
BANK_NAME = re.compile(r"((?:[A-Z][A-Za-z&.']*\s)+Bank)\b")
TAX_ID = re.compile(r"\b(?:EIN|Fed(?:eral)?\.? Tax ID|Federal tax ID)\s*:?\s*(\d{2}-\d{7})\b", re.IGNORECASE)
CREDIT = re.compile(r"\bcredit\s+(note|memo)\b", re.IGNORECASE)


def parse_invoice(pages: list[PageText]) -> tuple[InvoiceData | None, list[str]]:
    """Return (invoice, []) when every check proves the reading, else (None, reasons it could not)."""
    lines = [(p.number, line.strip()) for p in pages for line in p.text.splitlines() if line.strip()]
    reasons: list[str] = []

    items, item_rows, bad_rows = _line_items(lines)
    if bad_rows:
        reasons.append(f"{len(bad_rows)} line(s) where qty x price is not the amount")
    if not items:
        reasons.append("no line items recognised")

    vendor = _vendor(pages[0])
    if not vendor:
        reasons.append("vendor not found in the vendor master")

    number = _required("invoice number", [m for pattern in INVOICE_NUMBER for m in _find(pattern, lines)
                                          if any(ch.isdigit() for ch in m[1])], reasons, key=invoice_key)
    issued = _required("invoice date", [(p, _iso(v), q) for p, v, q in _find(INVOICE_DATE, lines) if _iso(v)], reasons)
    due = _unique("due date", [(p, _iso(v), q) for p, v, q in _find(DUE_DATE, lines) if _iso(v)], None)

    po_hits = [(p, po_key(v), q) for p, v, q in _find(PO_NUMBER, lines)]
    po = _unique("PO number", po_hits, reasons)
    if not po_hits and any(PO_LABEL.search(text) for _, text in lines):
        reasons.append("a PO label is printed but its number could not be read")

    money = _money_lines([row for row in lines if row not in item_rows])
    total = _required("total", money["total"], reasons)
    subtotal = _unique("subtotal", money["subtotal"], reasons)
    tax = _unique("tax", money["tax"], reasons)
    freight = _unique("freight", money["freight"], reasons)

    if not reasons:
        reasons += _reconcile(items, subtotal, tax, freight, total, money["tax_included"])
    if reasons:
        return None, reasons

    all_text = "\n".join(p.text for p in pages)
    routing = ROUTING.search(all_text)
    account = ACCOUNT.search(all_text)
    remit_line = next((t for _, t in lines if ROUTING.search(t) or ACCOUNT.search(t)), "")
    bank = BANK_NAME.search(remit_line)
    tax_id = TAX_ID.search(all_text)
    hint = next((t for _, t in lines if t.lower().startswith("re:")), None)
    note = next((t for _, t in lines if t.upper().startswith("IMPORTANT") or t.lower().startswith("credit against")), None)
    total_value = float(total[1])
    return InvoiceData(
        document_type="credit_note" if CREDIT.search(all_text) or total_value < 0 else "invoice",
        vendor_name=Sourced(value=vendor[1], page=1, source_quote=vendor[1]),
        vendor_tax_id=tax_id.group(1) if tax_id else None,
        invoice_number=_sourced(number),
        invoice_date=_sourced(issued),
        due_date=_sourced(due),
        currency="USD" if "$" in all_text or "USD" in all_text else None,
        po_number=_sourced(po),
        po_hint=hint,
        lines=items,
        subtotal=float(subtotal[1]) if subtotal else None,
        tax_amount=float(tax[1]) if tax else money["included_tax"],
        tax_rate_pct=money["tax_rate"],
        tax_included_in_prices=money["tax_included"],
        freight=float(freight[1]) if freight else None,
        total=_sourced((total[0], f"{total_value:.2f}", total[2])),
        remit_bank_name=bank.group(1) if bank else None,
        remit_routing_number=Sourced(value=routing.group(1), page=None, source_quote=routing.group(0)) if routing
        else Sourced(value=None, page=None, source_quote=None),
        remit_account_number=Sourced(value=account.group(1), page=None, source_quote=account.group(0)) if account
        else Sourced(value=None, page=None, source_quote=None),
        notes=note,
    ), []


# ---------------------------------------------------------------- pieces

def _find(pattern: re.Pattern, lines) -> list[tuple[int, str, str]]:
    """Every match as (page, value, the matched text used as evidence)."""
    return [(page, m.group(m.lastindex or 0).strip(), m.group(0).strip())
            for page, text in lines for m in pattern.finditer(text)]


def _unique(name: str, hits: list, reasons: list[str] | None, key=lambda v: v):
    """At most one distinct value. Several different values = the document is ambiguous (a reason, if reasons given)."""
    distinct = {key(h[1]): h for h in hits if h[1] not in (None, "")}
    if len(distinct) > 1:
        if reasons is not None:
            reasons.append(f"more than one {name} ({', '.join(sorted(str(h[1]) for h in distinct.values()))})")
        return None
    return next(iter(distinct.values()), None)


def _required(name: str, hits: list, reasons: list[str], key=lambda v: v):
    """Exactly one distinct value, or a reason why not."""
    before = len(reasons)
    hit = _unique(name, hits, reasons, key)
    if hit is None and len(reasons) == before:
        reasons.append(f"{name} not found")
    return hit


def _sourced(hit) -> Sourced:
    if not hit:
        return Sourced(value=None, page=None, source_quote=None)
    page, value, quote = hit
    return Sourced(value=str(value), page=page, source_quote=quote)


def _iso(text: str) -> str | None:
    text = text.replace(".", "")
    for fmt in DATE_FORMATS:
        try:
            return datetime.strptime(text, fmt).date().isoformat()
        except ValueError:
            continue
    return None


def _amount(text: str) -> float:
    sign_a, sign_b, number = AMOUNT.search(text).groups()
    value = float(number.replace(",", ""))
    return -value if (sign_a or sign_b) else value


def _line_items(lines) -> tuple[list[LineItem], set, list]:
    items, rows, bad = [], set(), []
    for row in lines:
        text = row[1]
        matched = False
        for pattern in (LINE_AMOUNTS_LAST, LINE_QTY_FIRST):
            m = pattern.match(text)
            if not m:
                continue
            matched = True
            qty, price, amount = float(m["qty"]), abs(_amount(m["price"])), _amount(m["amount"])
            if abs(qty * price - abs(amount)) <= TOLERANCE:
                body = m["body"].strip()
                sku = SKU.match(body)
                items.append(LineItem(sku=sku.group(1) if sku else None, description=sku.group(2) if sku else body,
                                      quantity=qty, unit_price=price, amount=amount))
                rows.add(row)
                break
        else:
            if matched:
                bad.append(text)
    return items, rows, bad


def _money_lines(lines) -> dict:
    out = {"subtotal": [], "tax": [], "freight": [], "total": [], "tax_included": False,
           "tax_rate": None, "included_tax": None}
    for page, text in lines:
        if not AMOUNT.search(text):
            continue
        low = text.lower()
        value = _amount(list(AMOUNT.finditer(text))[-1].group(0))        # the amount is the last one on the line
        rate = re.search(r"(\d+(?:\.\d+)?)\s*%", text)
        if "subtotal" in low or "sub-total" in low or low.startswith("merchandise"):
            out["subtotal"].append((page, value, text))
        elif "tax" in low and "total" not in low:
            out["tax"].append((page, value, text))
            out["tax_rate"] = float(rate.group(1)) if rate else out["tax_rate"]
        elif "freight" in low or "shipping" in low:
            out["freight"].append((page, value, text))
        elif re.search(r"\b(total|balance due|amount due)\b", low):
            out["total"].append((page, value, text))
            if "include" in low and "tax" in low:          # e.g. "Total (includes 7.5% sales tax of $138.60)"
                out["tax_included"] = True
                out["tax_rate"] = float(rate.group(1)) if rate else None
                of = re.search(r"tax of\s*(" + MONEY + ")", text, re.IGNORECASE)
                out["included_tax"] = _amount(of.group(1)) if of else None
    return out


def _vendor(page: PageText) -> tuple[dict, str] | None:
    """The vendor is whichever vendor-master name (or alias) appears in the top of page 1; the longest wins."""
    top = "\n".join(page.text.splitlines()[:10])
    low = top.lower()
    best = None
    for v in db.vendors():
        for name in [v["name"], *v["aliases"].split("|")]:
            i = low.find(name.lower())
            if i >= 0 and (best is None or len(name) > len(best[1])):
                best = (v, top[i:i + len(name)])
    return best


def _reconcile(items, subtotal, tax, freight, total, tax_included) -> list[str]:
    line_sum = round(sum(i.amount for i in items), 2)
    tax_v = float(tax[1]) if tax else 0.0
    freight_v = float(freight[1]) if freight else 0.0
    total_v = float(total[1])
    problems = []
    if tax_included:
        if subtotal and min(abs(line_sum - float(subtotal[1])), abs(line_sum - tax_v - float(subtotal[1]))) > TOLERANCE:
            problems.append("lines do not add up to the subtotal")
        expected = line_sum + freight_v
    else:
        if subtotal and abs(line_sum - float(subtotal[1])) > TOLERANCE:
            problems.append(f"lines add up to {line_sum:.2f}, not the printed subtotal {float(subtotal[1]):.2f}")
        expected = (float(subtotal[1]) if subtotal else line_sum) + tax_v + freight_v
    if abs(expected - total_v) > TOLERANCE:
        problems.append(f"subtotal + tax + freight = {expected:.2f}, not the printed total {total_v:.2f}")
    return problems
