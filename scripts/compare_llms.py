"""Head-to-head benchmark of the invoice readers: same invoices, same prompt, same clean-up code, one model at a time.

  python scripts/compare_llms.py run openai/gpt-oss-120b 20     # one model; pause 20 s between calls (rate limits)
  python scripts/compare_llms.py summary                        # table of every saved result

Accuracy is scored field by field against the ground truth, and each reading is also pushed through the rules to
check the final decision. Results are saved in samples/benchmark/<model>.json.
"""
import json
import statistics
import sys
import tempfile
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests"), str(ROOT / "scripts")]

from app import config, db, extract  # noqa: E402
from app.pipeline import run_invoice, sample_files  # noqa: E402
from app.text import read_pages  # noqa: E402
from check_extraction import score  # noqa: E402
from judging import judge  # noqa: E402

OUT = ROOT / "samples" / "benchmark"


PRINTS_DUE_DATE = {"classic", "compact", "grid", "minimal"}      # the other layouts print no due date at all


def fields(data: dict, truth: dict, layout: str) -> dict[str, bool]:
    """The 9 decision-critical fields from check_extraction, plus 5 more for a finer comparison."""
    checks = score(data, truth)
    due = data["due_date"]["value"] if isinstance(data["due_date"], dict) else data["due_date"]
    checks.update({
        "vendor": (data["vendor_name"]["value"] or "").strip().lower() == truth["vendor_name"].lower(),
        "due_date": due == (truth["due_date"] if layout in PRINTS_DUE_DATE else None),
        "routing": data["remit_routing_number"]["value"] == truth["remit_routing"],
        "tax_included": data["tax_included_in_prices"] == truth.get("tax_included", False),
        "doc_type": data.get("document_type", "invoice") == truth.get("document_type", "invoice"),
    })
    return checks


def decision_ok(item: dict, extraction) -> bool:
    tmp = Path(tempfile.mkdtemp())
    config.STORAGE_DIR, config.DB_PATH, config.STAGE_PAUSE_S = tmp, tmp / "b.db", 0
    db.reset()
    if item["expected"].get("depends_on"):
        from conftest import sample
        dep = sample(item["expected"]["depends_on"])
        run_invoice(dep[0], extraction=dep[1])
    ok, _ = judge(item["expected"], run_invoice(item["path"], extraction=extraction)["decision"])
    return ok


def run(model: str, pause: float) -> None:
    provider = "groq" if "/" in model else "gemini"
    extract.GROQ_MODELS, extract.GEMINI_MODELS = [model], [model]
    if provider == "groq":
        extract.GEMINI_API_KEY = ""          # force this one model: no fallback to the other provider
    else:
        extract.GROQ_API_KEY = ""
    rows = []
    items = [i for i in sample_files() if "ground_truth" in i]
    for n, item in enumerate(items):
        if n and pause:
            time.sleep(pause)
        pages = read_pages(item["path"])
        started = time.perf_counter()
        try:
            result = extract.extract_invoice(item["path"], pages)
            seconds = round(time.perf_counter() - started, 2)
            data = result.data.model_dump()
            checks = fields(data, item["ground_truth"], item["layout"])
            row = {"scenario": item["scenario"], "ok": True, "seconds": seconds, "fields": checks,
                   "decision_ok": decision_ok(item, result.data), "waits": result.fallbacks, "data": data}
        except extract.ExtractionError as exc:
            row = {"scenario": item["scenario"], "ok": False, "seconds": round(time.perf_counter() - started, 2),
                   "error": str(exc)[:300]}
        rows.append(row)
        misses = [k for k, v in row.get("fields", {}).items() if not v]
        print(f"{model:24} {item['scenario']:6} {'read' if row['ok'] else 'FAILED'} {row['seconds']:6.1f}s "
              f"{'decision ok' if row.get('decision_ok') else 'decision WRONG' if row['ok'] else ''} "
              f"{'missed: ' + ','.join(misses) if misses else ''}", flush=True)
    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / f"{model.replace('/', '_')}.json").write_text(json.dumps({"model": model, "provider": provider,
                                                                     "rows": rows}, indent=2), encoding="utf-8")


def summary() -> None:
    table = []
    for path in sorted(OUT.glob("*.json")):
        d = json.loads(path.read_text(encoding="utf-8"))
        read = [r for r in d["rows"] if r["ok"]]
        total_fields = sum(len(r["fields"]) for r in read)
        right_fields = sum(sum(r["fields"].values()) for r in read)
        table.append({
            "model": d["model"], "provider": d["provider"],
            "answered": f"{len(read)}/{len(d['rows'])}",
            "field_acc": right_fields / total_fields if total_fields else 0,
            "fields": f"{right_fields}/{total_fields}",
            "decisions": f"{sum(r['decision_ok'] for r in read)}/{len(d['rows'])}",
            "decisions_n": sum(r["decision_ok"] for r in read),
            "median_s": statistics.median(r["seconds"] for r in read) if read else 0,
            "misses": sorted({f"{r['scenario']}:{k}" for r in read for k, v in r["fields"].items() if not v}),
            "failures": [f"{r['scenario']}: {r['error'][:80]}" for r in d["rows"] if not r["ok"]],
        })
    table.sort(key=lambda t: (-t["decisions_n"], -t["field_acc"], t["median_s"]))   # accuracy first, then speed
    print(f"{'rank':4} {'model':26} {'decisions':10} {'fields':12} {'field acc':9} {'answered':9} {'median s':8}")
    for i, t in enumerate(table, 1):
        print(f"{i:<4} {t['model']:26} {t['decisions']:10} {t['fields']:12} {t['field_acc']:8.1%} {t['answered']:9} "
              f"{t['median_s']:8.1f}")
    for t in table:
        if t["misses"] or t["failures"]:
            print(f"\n{t['model']}: missed {t['misses'] or 'nothing'}; failed {t['failures'] or 'never'}")


if __name__ == "__main__":
    if sys.argv[1] == "summary":
        summary()
    else:
        run(sys.argv[2], float(sys.argv[3]) if len(sys.argv) > 3 else 0)
