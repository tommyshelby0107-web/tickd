"""SQLite storage: reference data (vendors, POs), the invoice registry, and every run with its events."""
import csv
import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from . import config
from .normalize import invoice_key

SCHEMA = """
CREATE TABLE vendors (
  vendor_id TEXT PRIMARY KEY, name TEXT, aliases TEXT, tax_id TEXT, status TEXT, address TEXT,
  phone_on_file TEXT, email TEXT, bank_name TEXT, bank_account TEXT, bank_routing TEXT,
  expected_tax_rate REAL, payment_terms TEXT);
CREATE TABLE purchase_orders (
  po_number TEXT PRIMARY KEY, vendor_id TEXT, status TEXT, created_date TEXT, buyer TEXT, description TEXT);
CREATE TABLE po_lines (
  po_number TEXT, line_no INTEGER, sku TEXT, description TEXT, qty_ordered REAL, unit_price REAL,
  qty_received REAL, qty_invoiced REAL, PRIMARY KEY (po_number, line_no));
CREATE TABLE invoice_registry (
  id INTEGER PRIMARY KEY AUTOINCREMENT, vendor_id TEXT, invoice_number TEXT, invoice_key TEXT,
  invoice_date TEXT, subtotal REAL, total REAL, po_number TEXT, status TEXT, decided_at TEXT,
  run_id TEXT, file_hash TEXT);
CREATE TABLE runs (
  run_id TEXT PRIMARY KEY, file_name TEXT, file_hash TEXT, status TEXT, decision TEXT, owner TEXT,
  severity TEXT, vendor_name TEXT, invoice_number TEXT, total REAL, summary TEXT, queued_at TEXT, started_at TEXT,
  finished_at TEXT, seconds REAL, result_json TEXT,
  batch_id TEXT, source TEXT, source_detail TEXT);
CREATE TABLE batches (
  batch_id TEXT PRIMARY KEY, name TEXT, source TEXT, created_at TEXT, total INTEGER, skipped_json TEXT);
CREATE TABLE events (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, stage TEXT, status TEXT, summary TEXT, at TEXT,
  data_json TEXT);
CREATE TABLE ledger_entries (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, po_number TEXT, line_no INTEGER, qty REAL,
  amount REAL, at TEXT);
CREATE TABLE review_actions (
  id INTEGER PRIMARY KEY AUTOINCREMENT, run_id TEXT, action TEXT, reason TEXT, actor TEXT, at TEXT);
"""


def now() -> str:
    """UTC with an explicit offset, so browsers in any timezone show the right local time."""
    return datetime.now(timezone.utc).isoformat(timespec="milliseconds")


@contextmanager
def connect():
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def reset() -> None:
    """Recreate the database from the CSV seed data. Every demo starts from this state."""
    config.STORAGE_DIR.mkdir(parents=True, exist_ok=True)
    config.DB_PATH.unlink(missing_ok=True)
    with connect() as conn:
        conn.executescript(SCHEMA)
        _load_csv(conn, "vendors.csv", "vendors")
        _load_csv(conn, "purchase_orders.csv", "purchase_orders")
        _load_csv(conn, "po_lines.csv", "po_lines")
        for row in _read_csv("invoice_history.csv"):
            conn.execute(
                "INSERT INTO invoice_registry (vendor_id, invoice_number, invoice_key, invoice_date, subtotal, total,"
                " po_number, status, decided_at) VALUES (?,?,?,?,?,?,?,?,?)",
                (row["vendor_id"], row["invoice_number"], invoice_key(row["invoice_number"]), row["invoice_date"],
                 float(row["subtotal"]), float(row["total"]), row["po_number"], row["status"], row["decided_at"]))


def ensure() -> None:
    """Create the database if missing, or rebuild it if it was made by an older version of the schema."""
    if config.DB_PATH.exists():
        with connect() as conn:
            columns = {row[1] for row in conn.execute("PRAGMA table_info(runs)")}
        if "batch_id" in columns:
            return
    reset()


def _read_csv(name: str) -> list[dict]:
    with open(config.DATA_DIR / name, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


def _load_csv(conn: sqlite3.Connection, name: str, table: str) -> None:
    rows = _read_csv(name)
    cols = list(rows[0])
    conn.executemany(f"INSERT INTO {table} ({','.join(cols)}) VALUES ({','.join('?' * len(cols))})",
                     [tuple(r[c] for c in cols) for r in rows])


# ---------------------------------------------------------------- reference data

def vendors() -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM vendors ORDER BY vendor_id")]


def purchase_order(po_number: str) -> dict | None:
    with connect() as conn:
        head = conn.execute("SELECT * FROM purchase_orders WHERE po_number = ?", (po_number,)).fetchone()
        if not head:
            return None
        lines = conn.execute("SELECT * FROM po_lines WHERE po_number = ? ORDER BY line_no", (po_number,)).fetchall()
    return {**dict(head), "lines": [dict(l) for l in lines]}


def purchase_orders(vendor_id: str | None = None, open_only: bool = False) -> list[dict]:
    sql, args = "SELECT po_number FROM purchase_orders WHERE 1=1", []
    if vendor_id:
        sql, args = sql + " AND vendor_id = ?", [vendor_id]
    if open_only:
        sql += " AND status = 'Open'"
    with connect() as conn:
        numbers = [r[0] for r in conn.execute(sql + " ORDER BY po_number", args)]
    return [purchase_order(n) for n in numbers]


# ---------------------------------------------------------------- invoice registry (approved / paid invoices)

def registry(vendor_id: str | None = None) -> list[dict]:
    sql, args = "SELECT * FROM invoice_registry", []
    if vendor_id:
        sql, args = sql + " WHERE vendor_id = ?", [vendor_id]
    with connect() as conn:
        return [dict(r) for r in conn.execute(sql + " ORDER BY id", args)]


def registry_by_hash(file_hash: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM invoice_registry WHERE file_hash = ?", (file_hash,)).fetchone()
    return dict(row) if row else None


def record_approval(run_id: str, vendor_id: str, invoice: dict, po_number: str | None,
                    line_matches: list[dict], file_hash: str) -> None:
    """Approving an invoice consumes PO quantities and registers it so it can never be paid twice."""
    at = now()
    with connect() as conn:
        conn.execute(
            "INSERT INTO invoice_registry (vendor_id, invoice_number, invoice_key, invoice_date, subtotal, total,"
            " po_number, status, decided_at, run_id, file_hash) VALUES (?,?,?,?,?,?,?,?,?,?,?)",
            (vendor_id, invoice["number"], invoice_key(invoice["number"]), invoice["date"], invoice["subtotal"],
             invoice["total"], po_number, "Approved", at, run_id, file_hash))
        for m in line_matches:
            conn.execute("UPDATE po_lines SET qty_invoiced = qty_invoiced + ? WHERE po_number = ? AND line_no = ?",
                         (m["qty"], po_number, m["po_line_no"]))
            conn.execute("INSERT INTO ledger_entries (run_id, po_number, line_no, qty, amount, at)"
                         " VALUES (?,?,?,?,?,?)", (run_id, po_number, m["po_line_no"], m["qty"],
                                                    m.get("amount_net", m["amount"]), at))


# ---------------------------------------------------------------- runs and events

def create_run(run_id: str, file_name: str, file_hash: str, status: str = "running", batch_id: str | None = None,
               source: str = "upload", source_detail: str | None = None) -> None:
    at = now()
    with connect() as conn:
        conn.execute("INSERT INTO runs (run_id, file_name, file_hash, status, queued_at, started_at, batch_id, source,"
                     " source_detail) VALUES (?,?,?,?,?,?,?,?,?)",
                     (run_id, file_name, file_hash, status, at, at if status == "running" else None,
                      batch_id, source, source_detail))


def mark_running(run_id: str) -> None:
    with connect() as conn:
        conn.execute("UPDATE runs SET status = 'running', started_at = ? WHERE run_id = ?", (now(), run_id))


def queue_position(run_id: str) -> int:
    """How many invoices will be processed before this queued one (including the one running now)."""
    with connect() as conn:
        row = conn.execute("SELECT queued_at FROM runs WHERE run_id = ?", (run_id,)).fetchone()
        return conn.execute("SELECT COUNT(*) FROM runs WHERE status IN ('queued', 'running') AND run_id != ?"
                            " AND queued_at <= ?", (run_id, row["queued_at"])).fetchone()[0] if row else 0


def finish_run(run_id: str, result: dict) -> None:
    d, inv = result["decision"], result.get("invoice") or {}
    with connect() as conn:
        conn.execute(
            "UPDATE runs SET status = 'done', decision = ?, owner = ?, severity = ?, vendor_name = ?,"
            " invoice_number = ?, total = ?, summary = ?, finished_at = ?, seconds = ?, result_json = ?"
            " WHERE run_id = ?",
            (d["outcome"], d.get("owner"), d.get("severity"), inv.get("vendor_name"), inv.get("number"),
             inv.get("total"), d.get("summary"), now(), result.get("seconds"), json.dumps(result), run_id))


def add_event(run_id: str, stage: str, status: str, summary: str, data: dict | None = None) -> dict:
    event = {"run_id": run_id, "stage": stage, "status": status, "summary": summary, "at": now(), "data": data or {}}
    with connect() as conn:
        conn.execute("INSERT INTO events (run_id, stage, status, summary, at, data_json) VALUES (?,?,?,?,?,?)",
                     (run_id, stage, status, summary, event["at"], json.dumps(event["data"])))
    return event


def run(run_id: str) -> dict | None:
    with connect() as conn:
        row = conn.execute("SELECT * FROM runs WHERE run_id = ?", (run_id,)).fetchone()
    if not row:
        return None
    out = dict(row)
    out["result"] = json.loads(out.pop("result_json") or "null")
    return out


RUN_COLUMNS = ("run_id, file_name, status, decision, owner, severity, vendor_name, invoice_number, total, summary,"
               " queued_at, started_at, seconds, batch_id, source, source_detail")


def runs(limit: int = 200) -> list[dict]:
    with connect() as conn:
        rows = conn.execute(f"SELECT {RUN_COLUMNS} FROM runs ORDER BY queued_at DESC, rowid DESC LIMIT ?",
                            (limit,)).fetchall()
    return [dict(r) for r in rows]


# ---------------------------------------------------------------- batches (a folder of invoices processed together)

def create_batch(batch_id: str, name: str, source: str, total: int, skipped: list[str]) -> None:
    with connect() as conn:
        conn.execute("INSERT INTO batches (batch_id, name, source, created_at, total, skipped_json) VALUES (?,?,?,?,?,?)",
                     (batch_id, name, source, now(), total, json.dumps(skipped)))


def batch(batch_id: str) -> dict | None:
    with connect() as conn:
        head = conn.execute("SELECT * FROM batches WHERE batch_id = ?", (batch_id,)).fetchone()
        if not head:
            return None
        rows = conn.execute(f"SELECT {RUN_COLUMNS} FROM runs WHERE batch_id = ? ORDER BY queued_at, rowid",
                            (batch_id,)).fetchall()
        items = []
        for r in rows:
            item = dict(r)
            if item["status"] == "running":     # show which stage it is on right now
                last = conn.execute("SELECT stage, summary FROM events WHERE run_id = ? ORDER BY id DESC LIMIT 1",
                                    (item["run_id"],)).fetchone()
                item["current_stage"] = dict(last) if last else None
            items.append(item)
    out = dict(head)
    out["skipped"] = json.loads(out.pop("skipped_json") or "[]")
    out["runs"] = items
    return out


def batches(limit: int = 50) -> list[dict]:
    with connect() as conn:
        heads = conn.execute("SELECT batch_id FROM batches ORDER BY created_at DESC LIMIT ?", (limit,)).fetchall()
    return [batch(h["batch_id"]) for h in heads]


def results() -> list[dict]:
    """Every finished run with its full result, for dashboard metrics."""
    with connect() as conn:
        rows = conn.execute("SELECT run_id, status, decision, seconds, started_at, result_json FROM runs"
                            " WHERE result_json IS NOT NULL").fetchall()
    return [{**{k: r[k] for k in ("run_id", "status", "decision", "seconds", "started_at")},
             "result": json.loads(r["result_json"])} for r in rows]


def events(run_id: str, after_id: int = 0) -> list[dict]:
    with connect() as conn:
        rows = conn.execute("SELECT * FROM events WHERE run_id = ? AND id > ? ORDER BY id", (run_id, after_id)).fetchall()
    return [{**{k: r[k] for k in ("id", "run_id", "stage", "status", "summary", "at")}, "data": json.loads(r["data_json"])}
            for r in rows]


def record_review(run_id: str, action: str, reason: str, actor: str = "AP reviewer") -> None:
    """A human resolved a held invoice. The run keeps its original automated decision in result_json."""
    with connect() as conn:
        conn.execute("INSERT INTO review_actions (run_id, action, reason, actor, at) VALUES (?,?,?,?,?)",
                     (run_id, action, reason, actor, now()))
        conn.execute("UPDATE runs SET status = 'resolved', decision = ? WHERE run_id = ?", (action, run_id))


def review_actions(run_id: str) -> list[dict]:
    with connect() as conn:
        return [dict(r) for r in conn.execute("SELECT * FROM review_actions WHERE run_id = ? ORDER BY id", (run_id,))]
