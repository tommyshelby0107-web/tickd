"""Web app: the API, the live event stream and the HTML pages, all served by one FastAPI process.

Run:  uvicorn app.main:app --reload
"""
import asyncio
import json
import shutil
import threading
from collections import Counter
from contextlib import asynccontextmanager
from datetime import datetime
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse, Response, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from . import config, db
from .pipeline import STAGES, new_run_id, run_invoice, sample_files
from .text import page_png

STATIC = config.ROOT / "static"
MAX_UPLOAD_BYTES = 10 * 1024 * 1024


def uploads_dir() -> Path:
    return config.STORAGE_DIR / "uploads"


@asynccontextmanager
async def lifespan(_: FastAPI):
    db.ensure()
    yield


app = FastAPI(title="Invoice Agent", lifespan=lifespan)
app.mount("/static", StaticFiles(directory=STATIC), name="static")


# ---------------------------------------------------------------- pages

@app.get("/", include_in_schema=False)
def dashboard_page():
    return FileResponse(STATIC / "index.html")


@app.get("/run", include_in_schema=False)
@app.get("/runs/{run_id}", include_in_schema=False)
def run_page(run_id: str | None = None):
    return FileResponse(STATIC / "run.html")


@app.get("/reference", include_in_schema=False)
def reference_page():
    return FileResponse(STATIC / "reference.html")


# ---------------------------------------------------------------- runs

@app.get("/api/config")
def app_config():
    providers = [name for name, key in (("Groq", config.GROQ_API_KEY), ("Gemini", config.GEMINI_API_KEY)) if key]
    return {"stages": [{"key": k, "label": label} for k, label in STAGES], "llm_providers": providers,
            "extraction_mode": config.EXTRACTION_MODE, "policy_version": config.POLICY["version"]}


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
    elif file:
        content = await file.read()
        if not content.startswith(b"%PDF"):
            raise HTTPException(400, "Please upload a PDF file.")
        if len(content) > MAX_UPLOAD_BYTES:
            raise HTTPException(400, "PDF is larger than 10 MB.")
        path = folder / Path(file.filename or "invoice.pdf").name
        path.write_bytes(content)
    else:
        raise HTTPException(400, "Send a PDF file or a sample name.")
    threading.Thread(target=run_invoice, args=(path, run_id), daemon=True).start()
    return {"run_id": run_id}


@app.get("/api/runs")
def list_runs():
    return db.runs()


@app.get("/api/runs/{run_id}")
def get_run(run_id: str):
    run = db.run(run_id)
    if not run:
        raise HTTPException(404, "Run not found")
    run["review_actions"] = db.review_actions(run_id)
    return run


@app.get("/api/runs/{run_id}/events")
async def run_events(run_id: str):
    """Server-Sent Events: replay what is stored, then keep sending new stage events until the decision."""
    async def stream():
        last_id, waited = 0, 0.0
        while waited < 300:
            for event in db.events(run_id, last_id):
                last_id = event["id"]
                yield f"data: {json.dumps(event)}\n\n"
                if event["stage"] == "decide" and event["status"] != "running":
                    yield "event: end\ndata: {}\n\n"
                    return
            await asyncio.sleep(0.3)
            waited += 0.3
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
    return {"vendors": vendors, "purchase_orders": pos, "registry": db.registry(), "policy": config.POLICY}


@app.post("/api/admin/reset")
def reset_demo():
    db.reset()
    shutil.rmtree(uploads_dir(), ignore_errors=True)
    return {"ok": True, "at": datetime.now().isoformat(timespec="seconds")}
