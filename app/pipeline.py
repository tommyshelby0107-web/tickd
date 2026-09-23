"""Run one invoice through the 8 stages, recording an event as each stage starts and finishes."""
import hashlib
import json
import time
import traceback
import uuid
from dataclasses import asdict
from pathlib import Path
from typing import Callable

from . import config, db
from .config import POLICY, SAMPLES_DIR
from .decide import decide
from .extract import ExtractionError, InvoiceData, extract_invoice
from .normalize import to_float
from .rules import PASS, Context, Finding, duplicate_check, line_match, po_match, validate, vendor_check
from .text import read_pages

STAGES = [("intake", "Intake"), ("extract", "Extract"), ("validate", "Validate"), ("vendor", "Vendor check"),
          ("duplicates", "Duplicate check"), ("po", "PO match"), ("lines", "Line match"), ("decide", "Decide")]
CHECKS = [("validate", validate), ("vendor", vendor_check), ("duplicates", duplicate_check),
          ("po", po_match), ("lines", line_match)]
SEVERITY = ["pass", "note", "review", "return", "reject"]

Listener = Callable[[dict], None]


def new_run_id() -> str:
    return uuid.uuid4().hex[:8]


def run_invoice(pdf_path: Path, run_id: str | None = None, listener: Listener | None = None,
                extraction: InvoiceData | None = None) -> dict:
    """Process one PDF end to end. Pass `extraction` to skip the LLM (tests, offline runs)."""
    run_id = run_id or new_run_id()
    started = time.perf_counter()
    file_hash = hashlib.sha256(pdf_path.read_bytes()).hexdigest()
    db.create_run(run_id, pdf_path.name, file_hash)
    done: set[str] = set()

    def emit(stage: str, status: str, summary: str, data: dict | None = None) -> None:
        event = db.add_event(run_id, stage, status, summary, data)
        if status != "running":
            done.add(stage)
        if listener:
            listener(event)

    result = {"run_id": run_id, "file_name": pdf_path.name, "file_hash": file_hash,
              "policy_version": POLICY["version"], "findings": [], "invoice": None}
    try:
        emit("intake", "running", "Reading the document")
        pages = read_pages(pdf_path)
        scanned = [p for p in pages if p.source == "ocr"]
        if scanned:
            confidence = min(p.ocr_confidence or 0 for p in scanned)
            intake = f"Scanned PDF, {len(pages)} page(s), OCR confidence {confidence:.0f}%"
        else:
            intake = f"Digital PDF, {len(pages)} page(s), text layer read"
        result["document"] = {"pages": len(pages), "type": "scanned" if scanned else "digital",
                              "ocr_confidence": [p.ocr_confidence for p in pages]}
        emit("intake", "pass", intake, result["document"])

        emit("extract", "running", "Reading invoice fields with the LLM")
        if extraction is None and config.EXTRACTION_MODE == "cached":
            extraction = cached_extraction(file_hash)
            if extraction:
                result["extraction"] = {"model": "cached extraction (no LLM call)"}
        if extraction is None:
            ext = extract_invoice(pdf_path, pages)
            invoice = ext.data
            result["extraction"] = {"model": ext.model, "seconds": ext.seconds, "input_tokens": ext.input_tokens,
                                    "output_tokens": ext.output_tokens, "image_pages": ext.image_pages,
                                    "fallbacks": ext.fallbacks}
        else:
            invoice = extraction
            result.setdefault("extraction", {"model": "provided (no LLM call)"})
        result["invoice"] = _invoice_summary(invoice)
        result["extracted"] = invoice.model_dump()
        emit("extract", "pass", f"{len(invoice.lines)} line(s), total {invoice.total.value or 'missing'} "
                                f"({result['extraction']['model']})", {"invoice": result["extracted"]})

        ctx = Context(invoice, pages, file_hash)
        for key, check in CHECKS:
            emit(key, "running", "Checking")
            summary, found = check(ctx)
            result["findings"] += [asdict(f) for f in found]
            worst = max((f.outcome for f in found), key=SEVERITY.index, default=PASS)
            time.sleep(config.STAGE_PAUSE_S)
            emit(key, worst, summary, {"findings": [asdict(f) for f in found]})

        emit("decide", "running", "Applying the decision matrix")
        decision = decide([Finding(**f) for f in result["findings"]], ctx)
        if decision["outcome"] == "Approve":
            db.record_approval(run_id, ctx.vendor["vendor_id"], result["invoice"], ctx.po["po_number"],
                               ctx.line_matches, file_hash)
        result.update(decision=decision, vendor=_vendor_summary(ctx.vendor), po=ctx.po and ctx.po["po_number"],
                      po_inferred=ctx.po_inferred, po_candidates=ctx.po_candidates, line_matches=ctx.line_matches)
        emit("decide", decision["outcome"].lower().replace(" ", "_"), decision["summary"], {"decision": decision})

    except ExtractionError as exc:
        failure = f"The invoice could not be read automatically: {exc}"
    except Exception as exc:  # any failure ends in human review, never in approval
        traceback.print_exc()
        failure = f"Processing error: {exc}"
    else:
        failure = None
    if failure:
        result["decision"] = _manual_review(failure)
        pending = [key for key, _ in STAGES[:-1] if key not in done]
        for i, key in enumerate(pending):
            emit(key, "error" if i == 0 else "skipped", failure if i == 0 else "Not run")
        emit("decide", "review", result["decision"]["summary"], {"decision": result["decision"]})

    result["seconds"] = round(time.perf_counter() - started, 2)
    db.finish_run(run_id, result)
    return result


SAMPLE_SETS = {"demo": SAMPLES_DIR, "holdout": SAMPLES_DIR / "holdout"}   # holdout = never used to tune the rules


def sample_files() -> list[dict]:
    """Every prepared sample (demo and held-out) with its path, file hash and extraction-cache path."""
    items = []
    for set_name, folder in SAMPLE_SETS.items():
        manifest = folder / "manifest.json"
        if not manifest.exists():
            continue
        for item in json.loads(manifest.read_text(encoding="utf-8")):
            item["set"] = set_name
            item["path"] = folder / "invoices" / item["file"]
            item["cache"] = folder / "extracted" / f"{item['scenario']}.json"
            item["hash"] = hashlib.sha256(item["path"].read_bytes()).hexdigest()
            items.append(item)
    return items


def cached_extraction(file_hash: str) -> InvoiceData | None:
    for item in sample_files():
        if item["hash"] == file_hash and item["cache"].exists():
            return InvoiceData.model_validate(json.loads(item["cache"].read_text(encoding="utf-8"))["data"])
    return None


def _manual_review(reason: str) -> dict:
    return {"outcome": "Review", "owner": "AP", "severity": "normal", "summary": f"Held for AP review. {reason}",
            "next_action": "Process this invoice manually.", "reasons": ["X-00"], "notes": [], "message": None}


def _invoice_summary(invoice: InvoiceData) -> dict:
    return {"vendor_name": invoice.vendor_name.value, "number": invoice.invoice_number.value,
            "date": invoice.invoice_date.value, "subtotal": invoice.subtotal,
            "total": to_float(invoice.total.value), "po_number": invoice.po_number.value}


def _vendor_summary(vendor: dict | None) -> dict | None:
    if not vendor:
        return None
    return {k: vendor[k] for k in ("vendor_id", "name", "status", "phone_on_file", "email")}
