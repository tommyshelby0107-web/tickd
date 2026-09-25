"""Web app: the API, the live event stream and the HTML pages, all served by one FastAPI process.

Run:  uvicorn app.main:app --reload
"""
import asyncio
import hashlib
import json
import logging
import queue
import shutil
import threading
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Request, UploadFile
from fastapi.exceptions import RequestValidationError
from fastapi.responses import FileResponse, JSONResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, db, email_intake, refdata
from .config import uploads_dir
from .pipeline import STAGES, new_run_id, run_invoice, sample_files
from .text import page_png

STATIC = config.ROOT / "static"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


# ---------------------------------------------------------------- one work queue for every intake channel
# Uploads, folders and email all put invoices on this queue; one worker processes them in order.
# One at a time respects free-tier LLM rate limits and makes duplicates within a batch deterministic.

JOBS: "queue.Queue[tuple[Path, str]]" = queue.Queue()
_worker_started = threading.Event()


def _worker() -> None:
    while True:
        path, run_id = JOBS.get()
        try:
            run_invoice(path, run_id)
        except Exception:        # run_invoice already turns failures into a Review; this guards the worker itself
            logging.exception("run %s failed", run_id)
        finally:
            JOBS.task_done()


def enqueue(path: Path, source: str, source_detail: str | None = None, batch_id: str | None = None,
            run_id: str | None = None, email_from: str | None = None) -> str:
    run_id = run_id or new_run_id()
    db.create_run(run_id, path.name, hashlib.sha256(path.read_bytes()).hexdigest(), status="queued",
                  batch_id=batch_id, source=source, source_detail=source_detail, email_from=email_from)
    JOBS.put((path, run_id))
    return run_id


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.ensure()
    if not _worker_started.is_set():
        threading.Thread(target=_worker, daemon=True, name="invoice-worker").start()
        if config.email_enabled():
            email_intake.start_poller(enqueue)
        _worker_started.set()
    yield


app = FastAPI(title="tickd by Sid", lifespan=lifespan)


@app.exception_handler(RequestValidationError)
async def readable_validation_error(_: Request, exc: RequestValidationError):
    """Form mistakes come back as one readable sentence the page can show, not a list of objects."""
    parts = []
    for error in exc.errors():
        where = " ".join(str(p).replace("_", " ") for p in error["loc"][1:] if not isinstance(p, int))
        parts.append(f"{where}: {error['msg'].lower()}" if where else error["msg"])
    return JSONResponse(status_code=422, content={"detail": "; ".join(dict.fromkeys(parts)) + "."})
app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------------------------------------------------------------- pages

@app.get("/", include_in_schema=False)
def cover_page():
    return FileResponse(STATIC / "home.html")


@app.get("/dashboard", include_in_schema=False)
def dashboard_page():
    return FileResponse(STATIC / "index.html")


@app.get("/run", include_in_schema=False)
@app.get("/runs/{run_id}", include_in_schema=False)
def run_page(run_id: str | None = None):
    return FileResponse(STATIC / "run.html")


@app.get("/reference", include_in_schema=False)
def reference_page():
    return FileResponse(STATIC / "reference.html")


@app.get("/bulk", include_in_schema=False)
@app.get("/bulk/{batch_id}", include_in_schema=False)
def bulk_page(batch_id: str | None = None):
    return FileResponse(STATIC / "bulk.html")


@app.get("/inbox", include_in_schema=False)
def inbox_page():
    return FileResponse(STATIC / "inbox.html")


# ---------------------------------------------------------------- email

@app.get("/api/email")
def email_status():
    return {"enabled": config.email_enabled(), "address": config.EMAIL_ADDRESS or None,
            "poll_seconds": config.EMAIL_POLL_SECONDS, "trusted_forwarders": config.EMAIL_TRUSTED_FORWARDERS,
            **email_intake.STATUS, "emails": db.email_log()}


@app.post("/api/email/check")
def email_check_now():
    """The 'Check now' button: poll the inbox immediately instead of waiting for the next cycle."""
    if not config.email_enabled():
        raise HTTPException(409, "Email is not configured: set EMAIL_ADDRESS and EMAIL_APP_PASSWORD in .env")
    try:
        email_intake.poll_once(enqueue)
    except Exception as exc:
        raise HTTPException(502, f"Could not read the inbox: {exc}") from exc
    return email_status()


# ---------------------------------------------------------------- runs

@app.get("/api/config")
def app_config():
    keys = {"groq": config.GROQ_API_KEY, "gemini": config.GEMINI_API_KEY, "mistral": config.MISTRAL_API_KEY}
    providers = [name.title() for name in config.PROVIDER_ORDER if keys.get(name)]
    return {"stages": [{"key": k, "label": label} for k, label in STAGES], "llm_providers": providers,
            "extraction_mode": config.EXTRACTION_MODE, "policy_version": config.POLICY["version"],
            "email": config.EMAIL_ADDRESS if config.email_enabled() else None}


@app.get("/api/samples")
def samples():
    return [{k: s[k] for k in ("scenario", "title", "file", "type", "layout", "vendor_id", "set")} for s in sample_files()]


@app.post("/api/runs")
async def start_run(file: UploadFile | None = File(None), sample: str | None = Form(None)):
    run_id = new_run_id()
    folder = uploads_dir() / run_id
    folder.mkdir(parents=True, exist_ok=True)
    if sample:
        item = next((s for s in sample_files() if s["scenario"] == sample), None)
        if not item:
            raise HTTPException(404, f"Unknown sample {sample}")
        path = folder / item["file"]
        shutil.copyfile(item["path"], path)
        source = "sample"
    elif file:
        content = await file.read()
        problem = _pdf_problem(content)
        if problem:
            raise HTTPException(400, problem)
        path = folder / Path(file.filename or "invoice.pdf").name
        path.write_bytes(content)
        source = "upload"
    else:
        raise HTTPException(400, "Send a PDF file or a sample name.")
    enqueue(path, source, run_id=run_id)
    return {"run_id": run_id}


def _pdf_problem(content: bytes) -> str | None:
    if not content.startswith(b"%PDF"):
        return "not a PDF"
    if len(content) > MAX_UPLOAD_BYTES:
        return "larger than 10 MB"
    return None


@app.post("/api/batches")
async def start_batch(files: list[UploadFile] = File(...), name: str = Form("Uploaded files")):
    """Process a whole folder: every PDF is saved and queued in filename order; anything else is listed as skipped."""
    received = sorted(files, key=lambda f: (f.filename or "").lower())
    batch_id = new_run_id()
    accepted, skipped = [], []
    for f in received:
        filename = Path(f.filename or "file").name       # browsers send "Folder/sub/file.pdf" for folder uploads
        content = await f.read()
        problem = _pdf_problem(content)
        if problem:
            skipped.append(f"{filename} ({problem})")
            continue
        accepted.append((filename, content))
    if not accepted:
        raise HTTPException(400, "No PDF invoices found. Skipped: " + ", ".join(skipped))
    db.create_batch(batch_id, name, "folder", len(accepted), skipped)
    for filename, content in accepted:
        run_id = new_run_id()
        path = uploads_dir() / run_id / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        enqueue(path, "folder", source_detail=name, batch_id=batch_id, run_id=run_id)
    return {"batch_id": batch_id, "queued": len(accepted), "skipped": skipped}


@app.get("/api/batches")
def list_batches():
    return db.batches()


@app.get("/api/batches/{batch_id}")
def get_batch(batch_id: str):
    found = db.batch(batch_id)
    if not found:
        raise HTTPException(404, "Batch not found")
    return found


@app.get("/api/runs")
def list_runs():
    return db.runs()


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = db.run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    run["review_actions"] = db.review_actions(run_id)
    if run["status"] == "queued":
        run["queue_position"] = db.queue_position(run_id)
    return run


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str):
    """Server-Sent Events: replay what is stored, then keep sending new stage events until the decision."""
    async def stream():
        last_id, idle = 0, 0.0
        while idle < 300:          # give up only after 5 minutes with no new event (a queued run just waits)
            for event in db.events(run_id, last_id):
                last_id, idle = event["id"], 0.0
                yield f"data: {json.dumps(event)}\n\n"
                if event["stage"] == "decide" and event["status"] != "running":
                    yield "event: end\ndata: {}\n\n"
                    return
            await asyncio.sleep(0.3)
            idle += 0.3
        yield "event: end\ndata: {}\n\n"

    return StreamingResponse(stream(), media_type="text/event-stream", headers={"Cache-Control": "no-cache"})


def _run_file(run_id: str) -> Path:
    run = db.run(run_id)
    path = uploads_dir() / run_id / run["file_name"] if run else None
    if not path or not path.exists():
        raise HTTPException(404, "File not found")
    return path


@app.get("/api/runs/{run_id}/pages/{number}")
def run_page_image(run_id: str, number: int):
    return Response(page_png(_run_file(run_id), number, dpi=110), media_type="image/png")


@app.get("/api/runs/{run_id}/pdf")
def run_pdf(run_id: str):
    return FileResponse(_run_file(run_id), media_type="application/pdf")


class ReviewAction(BaseModel):
    action: str       # approve | reject | return
    reason: str


REVIEW_OUTCOMES = {"approve": "Approve", "reject": "Reject", "return": "Return to vendor"}


@app.post("/api/runs/{run_id}/review")
def review_run(run_id: str, body: ReviewAction):
    run = db.run(run_id)
    if not run or not run["result"]:
        raise HTTPException(404, "Run not found")
    if run["status"] != "done" or run["decision"] not in ("Review", "Return to vendor"):
        raise HTTPException(409, "Only held invoices can be reviewed.")
    if body.action not in REVIEW_OUTCOMES or not body.reason.strip():
        raise HTTPException(400, "Choose an action and give a reason.")
    result = run["result"]
    if body.action == "approve":
        if not (result.get("vendor") and result.get("po")):
            raise HTTPException(409, "Cannot approve without a matched vendor and PO.")
        if "V-07" in result["decision"]["reasons"]:
            raise HTTPException(409, "Cannot approve an invoice in another currency than its PO: the PO ledger "
                                     "would mix currencies.")
        db.record_approval(run_id, result["vendor"]["vendor_id"], result["invoice"], result["po"],
                           result.get("line_matches", []), result["file_hash"])
    db.record_review(run_id, REVIEW_OUTCOMES[body.action], body.reason.strip())
    return get_run(run_id)


# ---------------------------------------------------------------- dashboard and reference data

@app.get("/api/metrics")
def metrics():
    finished = db.results()
    automated = Counter(r["result"]["decision"]["outcome"] for r in finished)
    reasons = Counter(rule for r in finished for rule in r["result"]["decision"]["reasons"])
    open_reviews = [r for r in finished if r["status"] == "done" and r["decision"] == "Review"]
    seconds = [r["seconds"] for r in finished if r["seconds"]]
    total = len(finished)
    straight_through = automated["Approve"] + automated["Reject"]
    return {
        "total": total,
        "straight_through": straight_through,
        "straight_through_pct": round(100 * straight_through / total) if total else 0,
        "avg_seconds": round(sum(seconds) / len(seconds), 1) if seconds else 0,
        "open_reviews": len(open_reviews),
        "high_risk_open": sum(r["result"]["decision"]["severity"] == "high" for r in open_reviews),
        "resolved_by_people": sum(r["status"] == "resolved" for r in finished),
        "by_outcome": {k: automated[k] for k in ("Approve", "Review", "Return to vendor", "Reject")},
        "by_reason": reasons.most_common(8),
    }


@app.get("/api/reference")
def reference():
    vendors = [{**v, "bank_account": f"...{v['bank_account'][-4:]}"} for v in db.vendors()]
    pos = []
    for po in db.purchase_orders():
        value = sum(l["qty_ordered"] * l["unit_price"] for l in po["lines"])
        billed = sum(l["qty_invoiced"] * l["unit_price"] for l in po["lines"])
        pos.append({**po, "value": value, "billed": billed, "billed_pct": round(100 * billed / value, 1) if value else 0})
    return {"vendors": vendors, "purchase_orders": pos, "registry": db.registry(), "policy": config.POLICY,
            "next_po_number": db.next_po_number()}


@app.post("/api/vendors", status_code=201)
def add_vendor(body: refdata.VendorIn):
    try:
        vendor = refdata.add_vendor(body)
    except refdata.RefDataError as exc:
        raise HTTPException(422, str(exc)) from exc
    return {**vendor, "bank_account": f"...{vendor['bank_account'][-4:]}"}


@app.post("/api/purchase_orders", status_code=201)
def add_purchase_order(body: refdata.PurchaseOrderIn):
    try:
        return refdata.add_purchase_order(body)
    except refdata.RefDataError as exc:
        raise HTTPException(422, str(exc)) from exc


@app.post("/api/admin/reset")
def reset_demo():
    while not JOBS.empty():          # drop anything still waiting; its runs are about to be wiped
        try:
            JOBS.get_nowait()
            JOBS.task_done()
        except queue.Empty:
            break
    db.reset()
    shutil.rmtree(uploads_dir(), ignore_errors=True)
    return {"ok": True, "at": datetime.now().isoformat(timespec="seconds")}
