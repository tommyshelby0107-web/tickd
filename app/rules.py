"""Stages 3-7: the deterministic checks. Nothing in this file calls an LLM.

Every check returns a Finding - including passes - so the audit trail shows what was checked,
not only what failed. Rule IDs match the rule catalogue in the design pack (section 04).
"""
import re
from dataclasses import dataclass, field
from datetime import date, timedelta

from rapidfuzz import fuzz, utils

from . import config, db
from .config import POLICY
from .extract import InvoiceData, LineItem, Sourced
from .normalize import digits, invoice_key, money, parse_date, po_key, squash, to_float
from .text import PageText

PASS, NOTE, REVIEW, RETURN, REJECT = "pass", "note", "review", "return", "reject"


@dataclass
class Finding:
    rule: str
    outcome: str                    # pass | note | review | return | reject
    message: str
    owner: str | None = None        # who must act: AP, Buyer, Warehouse, Procurement, AP lead, Vendor
    severity: str = "normal"        # "high" for fraud signals
    details: dict = field(default_factory=dict)


@dataclass
class Context:
    """What the checks learn as they go; later stages build on earlier ones."""
    invoice: InvoiceData
    pages: list[PageText]
    file_hash: str
    vendor: dict | None = None
    po: dict | None = None
    po_inferred: bool = False
    po_candidates: list[dict] = field(default_factory=list)
    line_matches: list[dict] = field(default_factory=list)
    is_credit: bool = False         # a credit note: never paid, so payment matching does not apply
    email_from: str | None = None   # sender address, when the invoice arrived by email


def similarity(a: str | None, b: str | None) -> float:
    return fuzz.token_set_ratio(a or "", b or "", processor=utils.default_process)


# ---------------------------------------------------------------- stage 3: validate

def validate(ctx: Context) -> tuple[str, list[Finding]]:
    inv, found = ctx.invoice, []
    ctx.is_credit = is_credit_note(ctx)

    required = [("invoice number", inv.invoice_number), ("invoice date", inv.invoice_date),
                ("vendor name", inv.vendor_name), ("total", inv.total)]
    missing = [label for label, s in required if not (s.value or "").strip()]
    if missing:
        found.append(Finding("V-01", RETURN, f"Missing {', '.join(missing)}.", owner="Vendor",
                             details={"missing": missing}))
    else:
        found.append(Finding("V-01", PASS, "Invoice number, date, vendor and total are present."))

    tol = POLICY["arithmetic_tolerance"]
    sign = abs if ctx.is_credit else (lambda x: x)     # credit notes print negative amounts; check the maths on size
    line_sum = round(sum(sign(l.amount) for l in inv.lines), 2)
    subtotal = sign(inv.subtotal) if inv.subtotal is not None else line_sum
    total = sign(to_float(inv.total.value)) if to_float(inv.total.value) is not None else None
    if inv.tax_included_in_prices:
        # Lines already include tax. A "subtotal" may be printed gross (= lines) or net (= lines - tax); both are valid.
        subtotal_ok = min(abs(line_sum - subtotal), abs(line_sum - (inv.tax_amount or 0.0) - subtotal)) <= tol
        expected_total = round(line_sum + (inv.freight or 0.0), 2)
    else:
        subtotal_ok = abs(line_sum - subtotal) <= tol
        expected_total = round(subtotal + sign(inv.tax_amount or 0.0) + (inv.freight or 0.0), 2)
    problems = [f"'{l.description}' amount {money(l.amount)} is not qty x price"
                for l in inv.lines if abs(abs(l.quantity * l.unit_price) - sign(l.amount)) > tol]
    if not subtotal_ok:
        problems.append(f"lines add up to {money(line_sum)} but subtotal is {money(subtotal)}")
    if total is not None and abs(expected_total - total) > tol:
        problems.append(f"subtotal + tax + freight = {money(expected_total)} but total is {money(total)}")
    if problems:
        found.append(Finding("V-02", REVIEW, "Arithmetic does not reconcile: " + "; ".join(problems) + ".", owner="AP"))
    else:
        found.append(Finding("V-02", PASS, f"Lines, subtotal, tax and total reconcile to {money(total)}."))

    invoice_date = parse_date(inv.invoice_date.value)
    today = date.today()
    if inv.invoice_date.value and not invoice_date:
        found.append(Finding("V-03", REVIEW, f"Invoice date '{inv.invoice_date.value}' could not be read.", owner="AP"))
    elif invoice_date and invoice_date > today:
        found.append(Finding("V-03", REVIEW, f"Invoice is dated in the future ({invoice_date}).", owner="AP"))
    elif invoice_date and invoice_date < today - timedelta(days=POLICY["max_invoice_age_days"]):
        found.append(Finding("V-03", REVIEW, f"Invoice is more than {POLICY['max_invoice_age_days']} days old.", owner="AP"))
    elif invoice_date:
        found.append(Finding("V-03", PASS, f"Invoice date {invoice_date} is plausible."))

    found.append(check_document_type(ctx))
    found.append(check_evidence(ctx))
    ok = sum(f.outcome == PASS for f in found)
    return f"{ok} of {len(found)} checks passed", found


CREDIT_WORDS = re.compile(r"\bcredit\s+(note|memo)\b", re.IGNORECASE)


def is_credit_note(ctx: Context) -> bool:
    """The LLM's classification, backed by two deterministic signals: a negative total or 'credit note' printed."""
    total = to_float(ctx.invoice.total.value)
    return (ctx.invoice.document_type == "credit_note" or (total is not None and total < 0)
            or any(CREDIT_WORDS.search(p.text) for p in ctx.pages))


def check_document_type(ctx: Context) -> Finding:
    """V-06: only real invoices can be paid. A credit note must be applied against the vendor balance instead."""
    inv = ctx.invoice
    total = to_float(inv.total.value)
    if ctx.is_credit:
        return Finding("V-06", REVIEW, f"This is a credit note for {money(abs(total or 0))}, not a bill to pay. "
                                       "Apply it against the vendor's open invoices instead.", owner="AP",
                       details={"llm_type": inv.document_type, "total": total})
    if inv.document_type not in ("invoice", "", None):
        return Finding("V-06", REVIEW, f"This document looks like a {inv.document_type}, not an invoice.", owner="AP")
    return Finding("V-06", PASS, "Document is an invoice.")


CRITICAL_FIELDS = [("invoice_number", "invoice number"), ("invoice_date", "invoice date"), ("total", "total"),
                   ("po_number", "PO number"), ("remit_account_number", "bank account")]


def check_evidence(ctx: Context) -> Finding:
    """V-05: the LLM's quote for each critical field must really be on the page, and legible if OCR'd."""
    texts = {p.number: squash(p.text) for p in ctx.pages}
    unverified, checked = [], []
    for attr, label in CRITICAL_FIELDS:
        sourced: Sourced = getattr(ctx.invoice, attr)
        if not sourced.value:
            continue
        checked.append(label)
        reason = _evidence_problem(attr, sourced, ctx.pages, texts)
        if reason:
            unverified.append(f"{label} ({reason})")
    if unverified:
        return Finding("V-05", REVIEW, "Could not verify against the document: " + "; ".join(unverified) + ".",
                       owner="AP", details={"unverified": unverified})
    return Finding("V-05", PASS, f"Verified {len(checked)} key fields against the document text.",
                   details={"verified": checked})


def _evidence_problem(attr: str, sourced: Sourced, pages: list[PageText], texts: dict[int, str]) -> str | None:
    quote = squash(sourced.source_quote)
    if not quote:
        return "no source quote"
    page = next((p for p in pages if quote in texts[p.number]), None)
    if page is None:
        return "quote not found in page text"
    value = sourced.value or ""
    if attr == "total" and digits(f"{to_float(value) or 0:.2f}") not in digits(quote):
        return "value not in quote"
    if attr in ("invoice_number", "po_number", "remit_account_number") and digits(value) not in digits(quote):
        return "value not in quote"
    if page.source == "ocr":
        confidence = {}
        for word, conf in page.words:
            confidence[squash(word)] = max(conf, confidence.get(squash(word), 0))
        scores = [confidence[t] for t in quote.split() if t in confidence]
        if scores and min(scores) < POLICY["ocr_confidence_min"]:
            return f"OCR confidence {min(scores):.0f}"
    return None


# ---------------------------------------------------------------- stage 4: vendor

def vendor_check(ctx: Context) -> tuple[str, list[Finding]]:
    inv, found = ctx.invoice, []
    vendors = db.vendors()
    tax_id = digits(inv.vendor_tax_id)
    match, how = None, ""
    if tax_id:
        match = next((v for v in vendors if digits(v["tax_id"]) == tax_id), None)
        how = "tax ID"
    if not match and inv.vendor_name.value:
        scored = [(max(similarity(inv.vendor_name.value, n) for n in [v["name"], *v["aliases"].split("|")]), v)
                  for v in vendors]
        best_score, best = max(scored, key=lambda s: s[0])
        if best_score >= POLICY["vendor_name_match_min"]:
            match, how = best, f"name ({best_score:.0f}% similar)"
    if not match:
        found.append(Finding("VM-01", REVIEW, f"Vendor '{inv.vendor_name.value}' is not in the vendor master.",
                             owner="Procurement"))
        return "Vendor not found", found

    ctx.vendor = v = match
    found.append(Finding("VM-01", PASS, f"Matched {v['name']} ({v['vendor_id']}) by {how}."))

    if v["status"] == "Blocked":
        found.append(Finding("VM-02", REJECT, f"{v['name']} is Blocked in the vendor master; its invoices cannot be paid.",
                             owner="Procurement"))
    else:
        found.append(Finding("VM-02", PASS, "Vendor is active."))

    printed = digits(inv.remit_account_number.value)
    on_file = digits(v["bank_account"])
    if not printed:
        found.append(Finding("VM-03", PASS, "No bank details printed; payment goes to the account on file."))
    elif printed == on_file:
        found.append(Finding("VM-03", PASS, f"Bank account ...{printed[-4:]} matches the vendor master."))
    else:
        found.append(Finding(
            "VM-03", REVIEW,
            f"Bank account on the invoice (...{printed[-4:]}, {inv.remit_bank_name or 'unknown bank'}) does not match "
            f"the vendor master (...{on_file[-4:]}, {v['bank_name']}). Hold payment and verify by calling "
            f"{v['phone_on_file']} - the number on file, not one printed on the invoice.",
            owner="AP lead", severity="high",
            details={"printed_account": printed, "account_on_file": on_file, "invoice_note": inv.notes}))

    sender = check_sender(ctx, v)
    if sender:
        found.append(sender)

    expected = (v["expected_tax_rate"] or 0) * 100
    subtotal = inv.subtotal or sum(l.amount for l in inv.lines)
    if inv.tax_included_in_prices:
        found.append(Finding("V-04", NOTE, "Prices include tax; tax-rate check not applied."))
    elif subtotal:
        actual = (inv.tax_amount or 0) / subtotal * 100
        if abs(actual - expected) > POLICY["tax_rate_tolerance_pp"]:
            found.append(Finding("V-04", REVIEW, f"Tax charged at {actual:.2f}%, but {v['name']} should charge "
                                                 f"{expected:.2f}%.", owner="AP"))
        else:
            found.append(Finding("V-04", PASS, f"Tax rate {actual:.2f}% matches the expected {expected:.2f}%."))
    return f"{v['name']} ({v['vendor_id']})", found


def check_sender(ctx: Context, vendor: dict) -> Finding | None:
    """VM-04: an emailed invoice should come from the vendor's own domain. A lookalike domain is a fraud signal."""
    sender = (ctx.email_from or "").lower()
    if not sender:
        return None                     # not emailed: nothing to check
    sender_domain = sender.rsplit("@", 1)[-1]
    vendor_domain = (vendor.get("email") or "").lower().rsplit("@", 1)[-1]
    details = {"sender": sender, "vendor_domain": vendor_domain}
    if sender in config.EMAIL_TRUSTED_FORWARDERS:
        return Finding("VM-04", NOTE, f"Forwarded by {sender}, a trusted internal address; the original sender "
                                      "cannot be checked.", details=details)
    if vendor_domain and (sender_domain == vendor_domain or sender_domain.endswith("." + vendor_domain)):
        return Finding("VM-04", PASS, f"Emailed from {sender_domain}, {vendor['name']}'s domain on file.")
    if any(sender_domain == d or sender_domain.endswith("." + d) for d in POLICY["sender_platform_domains"]):
        return Finding("VM-04", PASS, f"Emailed via the invoicing platform {sender_domain}.")
    if vendor_domain and _domain_similarity(sender_domain, vendor_domain) >= POLICY["sender_lookalike_min"]:
        return Finding("VM-04", REVIEW, f"Lookalike sender domain: emailed from {sender_domain}, but {vendor['name']}'s "
                                        f"domain on file is {vendor_domain}. This is a common impersonation pattern. "
                                        f"Verify by calling {vendor['phone_on_file']} before any payment.",
                       owner="AP lead", severity="high", details=details)
    return Finding("VM-04", REVIEW, f"Emailed from {sender}, not from {vendor['name']}'s domain on file "
                                    f"({vendor_domain or 'none'}). Confirm the vendor sent it.", owner="AP",
                   details=details)


def _domain_similarity(a: str, b: str) -> float:
    """Compare the names without TLD or hyphens: 'apex-fasteners-billing.com' vs 'apexfasteners.example' -> 100."""
    def base(domain: str) -> str:
        return domain.rsplit(".", 1)[0].replace("-", "").replace(".", "")
    return fuzz.partial_ratio(base(a), base(b))


# ---------------------------------------------------------------- stage 5: duplicates

def duplicate_check(ctx: Context) -> tuple[str, list[Finding]]:
    inv, found = ctx.invoice, []
    same_file = db.registry_by_hash(ctx.file_hash)
    if same_file:
        found.append(Finding("D-01", REJECT, f"This exact file was already processed as invoice "
                                             f"{same_file['invoice_number']} ({same_file['status'].lower()} "
                                             f"{same_file['decided_at'][:10]}).", details=same_file))
    else:
        found.append(Finding("D-01", PASS, "File has not been processed before."))

    if not ctx.vendor:
        return "Skipped vendor-level checks: vendor unknown", found
    earlier = db.registry(ctx.vendor["vendor_id"])
    key = invoice_key(inv.invoice_number.value)
    twin = next((r for r in earlier if key and r["invoice_key"] == key), None)
    if twin:
        found.append(Finding("D-02", REJECT, f"Duplicate of invoice {twin['invoice_number']} from this vendor, already "
                                             f"{twin['status'].lower()} on {twin['decided_at'][:10]}.", details=twin))
    elif key:
        found.append(Finding("D-02", PASS, f"No earlier invoice from this vendor with key {key}."))

    total, when = to_float(inv.total.value), parse_date(inv.invoice_date.value)
    near = [r for r in earlier
            if r["invoice_key"] != key and total is not None and when
            and abs(r["total"] - total) <= POLICY["near_duplicate_amount"]
            and abs((parse_date(r["invoice_date"]) - when).days) <= POLICY["near_duplicate_days"]]
    if near:
        r = near[0]
        found.append(Finding("D-03", REVIEW, f"Possible duplicate: invoice {r['invoice_number']} for {money(r['total'])} "
                                             f"dated {r['invoice_date']} has a different number but the same amount.",
                             owner="AP", details=r))
    else:
        found.append(Finding("D-03", PASS, "No near-duplicate by amount and date."))
    issues = [f for f in found if f.outcome != PASS]
    return ("Duplicate found" if issues else "No duplicates"), found


# ---------------------------------------------------------------- stage 6: PO match

def po_match(ctx: Context) -> tuple[str, list[Finding]]:
    inv, found = ctx.invoice, []
    ref = po_key(inv.po_number.value)
    if ref:
        po = db.purchase_order(ref)
        if not po:
            found.append(Finding("P-01", REVIEW, f"{ref} printed on the invoice does not exist.", owner="AP"))
            return f"{ref} not found", found
        ctx.po = po
        found.append(Finding("P-01", PASS, f"{ref} found in the PO register."))
        owner_vendor = next(v for v in db.vendors() if v["vendor_id"] == po["vendor_id"])
        if not ctx.vendor:
            # An unknown company quoting one of OUR real PO numbers is how impersonation fraud starts.
            found.append(Finding(
                "P-02", REVIEW,
                f"{ref} belongs to {owner_vendor['name']}, but this invoice is from '{inv.vendor_name.value}', who is not "
                f"in the vendor master. Possible impersonation: confirm with {owner_vendor['name']} on "
                f"{owner_vendor['phone_on_file']} (number on file) before anything is paid.",
                owner="AP lead", severity="high", details={"po_vendor": owner_vendor["vendor_id"]}))
        elif po["vendor_id"] != ctx.vendor["vendor_id"]:
            found.append(Finding("P-02", REVIEW, f"{ref} belongs to {owner_vendor['name']}, not "
                                                 f"{ctx.vendor['name']}.", owner="AP"))
        else:
            found.append(Finding("P-02", PASS, "PO belongs to this vendor."))
        if po["status"] != "Open":
            found.append(Finding("P-03", REVIEW, f"{ref} is {po['status']}.", owner="Buyer"))
        else:
            found.append(Finding("P-03", PASS, "PO is open."))
        found.append(Finding("P-04", PASS, "PO number is printed on the invoice."))
        return f"{ref} (printed on invoice)", found

    if not ctx.vendor:
        found.append(Finding("P-01", REVIEW, "No PO number printed and the vendor is unknown, so no PO can be found.",
                             owner="AP"))
        return "No PO", found
    candidates = sorted((_score_po(inv, po) for po in db.purchase_orders(ctx.vendor["vendor_id"], open_only=True)),
                        key=lambda c: c["score"], reverse=True)
    ctx.po_candidates = [{k: c[k] for k in ("po_number", "score", "line_similarity", "amount_fit")}
                         for c in candidates[:3]]
    best = candidates[0] if candidates else None
    runner_up = candidates[1]["score"] if len(candidates) > 1 else 0.0
    if best and best["score"] >= POLICY["po_inference_min_score"] and best["score"] - runner_up >= POLICY["po_inference_min_gap"]:
        ctx.po, ctx.po_inferred = best["po"], True
        found.append(Finding("P-01", PASS, f"No PO number printed; {best['po_number']} identified from vendor, lines and amount."))
        found.append(Finding("P-04", REVIEW, f"{best['po_number']} was inferred (match score {best['score']:.2f}, "
                                             f"next best {runner_up:.2f}). Confirm it before approval - inferred matches "
                                             f"are never auto-approved.", owner="AP",
                             details={"candidates": ctx.po_candidates, "po_hint": inv.po_hint}))
        return f"{best['po_number']} (inferred)", found
    found.append(Finding("P-01", REVIEW, "No PO number printed and no open PO matches confidently.", owner="AP",
                         details={"candidates": ctx.po_candidates, "po_hint": inv.po_hint}))
    return "No confident PO match", found


def _score_po(inv: InvoiceData, po: dict) -> dict:
    """Score how well an open PO explains an invoice that has no PO number: 60% lines, 40% amount."""
    line_scores = [max(_line_similarity(line, pl) for pl in po["lines"]) / 100 for line in inv.lines]
    line_similarity = sum(line_scores) / len(line_scores) if line_scores else 0.0
    remaining = sum((pl["qty_ordered"] - pl["qty_invoiced"]) * pl["unit_price"] for pl in po["lines"])
    subtotal = inv.subtotal or sum(l.amount for l in inv.lines)
    amount_fit = max(0.0, 1 - abs(subtotal - remaining) / max(remaining, 1.0))
    score = round(0.6 * line_similarity + 0.4 * amount_fit, 2)
    return {"po_number": po["po_number"], "po": po, "score": score,
            "line_similarity": round(line_similarity, 2), "amount_fit": round(amount_fit, 2)}


def _line_similarity(line: LineItem, po_line: dict) -> float:
    if line.sku and line.sku.strip().upper() == po_line["sku"].upper():
        return 100.0
    return similarity(line.description, po_line["description"])


# ---------------------------------------------------------------- stage 7: line match

def line_match(ctx: Context) -> tuple[str, list[Finding]]:
    inv, po, found = ctx.invoice, ctx.po, []
    if ctx.is_credit:
        return "Skipped: a credit note is applied to the balance, not matched for payment", found
    if not po:
        return "Skipped: no PO to match against", found

    # PO prices are net of tax. If the invoice's prices include tax, compare them net of that tax.
    tax_note = ""
    net = 1.0
    if inv.tax_included_in_prices:
        rate = inv.tax_rate_pct if inv.tax_rate_pct is not None else ((ctx.vendor or {}).get("expected_tax_rate") or 0) * 100
        net = 1 / (1 + rate / 100)
        tax_note = f" (compared net of the {rate:g}% tax included in the prices)"

    unmatched = []
    for line in inv.lines:
        best = max(po["lines"], key=lambda pl: _line_similarity(line, pl))
        if _line_similarity(line, best) < 70:
            unmatched.append(line.description)
            continue
        ctx.line_matches.append({
            "description": line.description, "po_line_no": best["line_no"], "sku": best["sku"],
            "qty": line.quantity, "unit_price": line.unit_price, "amount": line.amount,
            "unit_price_net": round(line.unit_price * net, 4), "amount_net": round(line.amount * net, 2),
            "po_unit_price": best["unit_price"], "qty_ordered": best["qty_ordered"],
            "qty_received": best["qty_received"], "qty_invoiced_before": best["qty_invoiced"],
        })
    if unmatched:
        found.append(Finding("M-00", REVIEW, f"{len(unmatched)} line(s) are not on {po['po_number']}: "
                                             f"{'; '.join(unmatched)}.", owner="Buyer"))
    if not ctx.line_matches:    # nothing to compare: say so, rather than report prices and quantities as "passed"
        return f"0 of {len(inv.lines)} lines match {po['po_number']}; price and quantity checks not applicable", found

    tol = POLICY["price_tolerance_pct"]
    variances = [(m, (m["unit_price_net"] - m["po_unit_price"]) / m["po_unit_price"] * 100) for m in ctx.line_matches]
    over = [f"{m['description']}: {money(m['unit_price_net'])} vs PO {money(m['po_unit_price'])} ({pct:+.1f}%)"
            for m, pct in variances if abs(pct) > tol]
    small = [f"{m['description']} {pct:+.1f}%" for m, pct in variances if 0.005 < abs(pct) <= tol]
    if over:
        found.append(Finding("M-01", REVIEW, "Price above tolerance - " + "; ".join(over) + tax_note + ".", owner="Buyer"))
    elif small:
        found.append(Finding("M-01", NOTE, f"Price variance within {tol:g}% tolerance: " + "; ".join(small) + tax_note + "."))
    else:
        found.append(Finding("M-01", PASS, "All unit prices match the PO" + tax_note + "."))

    short = []
    for m in ctx.line_matches:
        available = m["qty_received"] - m["qty_invoiced_before"]
        if m["qty"] > available + 1e-9:
            owner = "Warehouse" if m["qty_received"] < m["qty_ordered"] else "Buyer"
            short.append((owner, f"{m['description']}: invoiced {m['qty']:g}, but only {available:g} received and not "
                                 f"yet billed ({m['qty_invoiced_before']:g} of {m['qty_ordered']:g} already invoiced)"))
    if short:
        found.append(Finding("M-02", REVIEW, "; ".join(s for _, s in short) + ".", owner=short[0][0]))
    else:
        found.append(Finding("M-02", PASS, "Quantities are within what was received and not yet billed."))

    po_value = sum(pl["qty_ordered"] * pl["unit_price"] for pl in po["lines"])
    billed_before = sum(pl["qty_invoiced"] * pl["unit_price"] for pl in po["lines"])
    this_invoice = sum(m["qty"] * m["po_unit_price"] for m in ctx.line_matches)
    after = billed_before + this_invoice
    cap = min(po_value * POLICY["header_tolerance_pct"] / 100, POLICY["header_tolerance_abs"])
    if after > po_value + cap + 0.005:
        found.append(Finding("M-03", REVIEW, f"{po['po_number']} would be billed {money(after)} of {money(po_value)} "
                                             f"({after / po_value * 100:.1f}%). Only {money(po_value - billed_before)} "
                                             f"remains billable.", owner="Buyer",
                             details={"po_value": po_value, "billed_before": billed_before, "after": after}))
    else:
        found.append(Finding("M-03", PASS, f"{po['po_number']} will be {after / po_value * 100:.1f}% billed after this invoice."))

    expected = round(this_invoice, 2)
    actual = round(sum(m["amount_net"] for m in ctx.line_matches), 2)
    variance = round(actual - expected, 2)
    allowed = min(expected * POLICY["header_tolerance_pct"] / 100, POLICY["header_tolerance_abs"])
    pct = variance / expected * 100 if expected else 0.0
    if abs(variance) > allowed + 0.005:
        found.append(Finding("M-04", REVIEW, f"Subtotal {money(actual)} is {money(variance)} ({pct:+.2f}%) away from PO "
                                             f"pricing of {money(expected)}; tolerance is {money(allowed)}.", owner="Buyer"))
    elif variance:
        found.append(Finding("M-04", NOTE, f"Subtotal is {money(variance)} ({pct:+.2f}%) above PO pricing, within the "
                                           f"{money(allowed)} tolerance."))
    else:
        found.append(Finding("M-04", PASS, f"Subtotal equals PO pricing ({money(expected)})."))

    freight = inv.freight or 0.0
    if not freight:
        found.append(Finding("M-05", PASS, "No unplanned charges."))
    elif freight <= POLICY["unplanned_charges_max"]:
        found.append(Finding("M-05", NOTE, f"Freight of {money(freight)} accepted (limit {money(POLICY['unplanned_charges_max'])})."))
    else:
        found.append(Finding("M-05", REVIEW, f"Freight of {money(freight)} is not on the PO and exceeds "
                                             f"{money(POLICY['unplanned_charges_max'])}.", owner="Buyer"))
    issues = [f for f in found if f.outcome in (REVIEW, RETURN, REJECT)]
    return f"{len(ctx.line_matches)} of {len(inv.lines)} lines matched" + (f", {len(issues)} issue(s)" if issues else ""), found
