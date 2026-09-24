"""Stage 8: turn the findings into one decision, an explanation, a next action and a draft message."""
from .normalize import money
from .rules import NOTE, PASS, REJECT, RETURN, REVIEW, Context, Finding

AP_EMAIL = "ap@meridian.example"

NEXT_STEP = {
    "VM-03": "Do not pay. The AP lead must call the vendor on the number on file and log the result before release.",
    "VM-04": "Do not pay yet. Confirm with the vendor, on the number on file, that they sent this invoice.",
    "P-02": "Do not pay. Ask the PO's real vendor, on the number on file, whether they sent this invoice. If not, "
            "reject it and alert IT security.",
    "V-06": "Do not pay. Apply the credit against the vendor's open invoices and file it with the original invoice.",
    "P-04": "Confirm the suggested PO is correct, then approve.",
    "P-01": "Find the right PO with the buyer, or route for non-PO approval.",
    "M-03": "Ask the vendor for a corrected invoice for the remaining quantity, or approve partially.",
    "M-02": "Confirm the goods were received before approving.",
    "M-01": "Confirm the price with the buyer or ask the vendor for a credit note.",
    "M-04": "Confirm the price with the buyer or ask the vendor for a credit note.",
    "M-05": "Confirm the extra charge with the buyer.",
    "M-00": "Check whether the extra line was ordered.",
    "D-03": "Check whether this is a duplicate of the earlier invoice.",
    "VM-01": "Onboard the vendor through procurement, or reject.",
    "V-02": "Check the figures on the PDF and correct or return to vendor.",
    "V-07": "Confirm the currency with the buyer: ask the vendor for an invoice in the PO's currency, or have "
            "procurement set up the PO in the invoice's currency.",
    "V-04": "Confirm the tax rate with the vendor.",
    "V-05": "Check the highlighted fields against the PDF.",
}


# When several issues fire, the one a reviewer should read first: fraud and duplicates, then whether the document
# can be trusted at all (not an invoice, missing data, its own maths wrong), then over-billing, price, quantity...
LEAD_PRIORITY = ["VM-03", "VM-04", "VM-02", "D-01", "D-02", "V-06", "D-03", "VM-01", "V-01", "V-02", "V-07", "M-03", "M-01",
                 "M-04", "M-02", "M-05", "M-00", "P-01", "P-02", "P-03", "P-04", "V-04", "V-05", "V-03"]


def _priority(f: Finding) -> int:
    return LEAD_PRIORITY.index(f.rule) if f.rule in LEAD_PRIORITY else len(LEAD_PRIORITY)


def decide(findings: list[Finding], ctx: Context) -> dict:
    by = {o: sorted((f for f in findings if f.outcome == o), key=_priority)
          for o in (REJECT, RETURN, REVIEW, NOTE, PASS)}
    inv = ctx.invoice
    vendor = ctx.vendor["name"] if ctx.vendor else (inv.vendor_name.value or "Unknown vendor")
    number = inv.invoice_number.value or "(no number)"
    total = inv.total.value

    if by[REJECT]:
        first = by[REJECT][0]
        outcome, owner, severity = "Reject", "AP", "normal"
        summary = f"Rejected. {first.message}"
        next_action = "Do not pay. Send the drafted reply."
        message = _reject_message(first, vendor, number, ctx)
    elif by[RETURN]:
        first = by[RETURN][0]
        outcome, owner, severity = "Return to vendor", "Vendor", "normal"
        summary = f"Returned to vendor. {first.message}"
        next_action = "Send the drafted email asking the vendor for a corrected invoice."
        message = _return_message(first, vendor, number, total, ctx)
    elif by[REVIEW]:
        high = [f for f in by[REVIEW] if f.severity == "high"]
        first = (high or by[REVIEW])[0]
        outcome, owner, severity = "Review", first.owner or "AP", "high" if high else "normal"
        others = len(by[REVIEW]) - 1
        summary = f"Held for {owner} review. {first.message}" + (f" Plus {others} other issue(s)." if others else "")
        next_action = NEXT_STEP.get(first.rule, "Review the findings and decide.")
        message = _review_message(by[REVIEW], owner, vendor, number)
    else:
        outcome, owner, severity = "Approve", None, "normal"
        po = ctx.po["po_number"] if ctx.po else "its PO"
        notes = f" {len(by[NOTE])} variance note(s) within tolerance." if by[NOTE] else ""
        summary = (f"Approved. {vendor} invoice {number} for {money(_float(total), ctx.currency)} passed every check "
                   f"against {po}.{notes}")
        next_action = "Added to the approved list and the PO ledger was updated. Include in the next payment run."
        message = None

    return {
        "outcome": outcome,
        "owner": owner,
        "severity": severity,
        "summary": summary,
        "next_action": next_action,
        "reasons": [f.rule for f in by[REJECT] + by[RETURN] + by[REVIEW]],
        "notes": [f.message for f in by[NOTE]],
        "message": message,
    }


def _float(value) -> float | None:
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _reject_message(first: Finding, vendor: str, number: str, ctx: Context) -> dict:
    if first.rule.startswith("D-"):
        earlier = first.details.get("invoice_number", number)
        return {"to": ctx.vendor["email"] if ctx.vendor else "vendor",
                "subject": f"Invoice {number} - already received",
                "body": f"Hello {vendor} accounts team,\n\nWe received invoice {number} again. It matches invoice "
                        f"{earlier}, which we have already processed, so it will not be paid a second time. "
                        f"No action is needed from you.\n\nKind regards,\nAccounts Payable, Meridian Industrial Supplies"}
    return {"to": "procurement@meridian.example", "subject": f"Rejected invoice {number} from {vendor}",
            "body": f"Invoice {number} from {vendor} was rejected: {first.message}\n\nPlease advise if this vendor "
                    f"should be reinstated before any payment is considered."}


def _return_message(first: Finding, vendor: str, number: str, total, ctx: Context) -> dict:
    missing = ", ".join(first.details.get("missing", [])) or "required information"
    po = f" referencing {ctx.invoice.po_number.value}" if ctx.invoice.po_number.value else ""
    amount = f" for {money(_float(total), ctx.currency)}" if _float(total) else ""
    return {"to": ctx.vendor["email"] if ctx.vendor else "vendor",
            "subject": f"Invoice {number} - information needed",
            "body": f"Hello {vendor} accounts team,\n\nWe received your invoice{amount}{po}, but we cannot process it "
                    f"because it is missing the {missing}.\n\nPlease send a corrected invoice to {AP_EMAIL}.\n\n"
                    f"Kind regards,\nAccounts Payable, Meridian Industrial Supplies"}


def _review_message(issues: list[Finding], owner: str, vendor: str, number: str) -> dict:
    bullet_list = "\n".join(f"- [{f.rule}] {f.message}" for f in issues)
    return {"to": owner, "subject": f"Action needed: invoice {number} from {vendor}",
            "body": f"Invoice {number} from {vendor} is on hold for your review.\n\n{bullet_list}\n\n"
                    f"Suggested next step: {NEXT_STEP.get(issues[0].rule, 'Review the findings and decide.')}"}
