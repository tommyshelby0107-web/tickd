"""Score the system on a sample set: did each invoice get the expected decision, for the right reason?

Every scenario runs on a fresh copy of the seed data, so the order of scenarios does not matter.

  python scripts/evaluate.py holdout truth    # rules only: perfect extraction from ground truth, no API calls
  python scripts/evaluate.py holdout live     # the real thing: text/OCR + LLM + rules (saves extractions)
  python scripts/evaluate.py demo cached      # reuse saved LLM extractions, no API calls
  python scripts/evaluate.py holdout live T-11   # just one scenario
"""
import json
import sys
import tempfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests"), str(ROOT / "scripts")]

from app import config, db  # noqa: E402
from app.extract import InvoiceData  # noqa: E402
from app.pipeline import run_invoice, sample_files  # noqa: E402
from check_extraction import score  # noqa: E402
from conftest import sample  # noqa: E402
from judging import judge  # noqa: E402


def extraction_for(item: dict, mode: str) -> InvoiceData | None:
    if mode == "truth":
        return sample(item["scenario"])[1]
    if mode == "cached" and item["cache"].exists():
        return InvoiceData.model_validate(json.loads(item["cache"].read_text(encoding="utf-8"))["data"])
    return None                                # live: the pipeline calls the LLM


def run_item(item: dict, mode: str, by_id: dict) -> dict:
    if item["expected"].get("depends_on"):     # e.g. EC-2 is only a duplicate once HP-1 is approved
        dep = by_id[item["expected"]["depends_on"]]
        run_invoice(dep["path"], extraction=extraction_for(dep, mode))
    result = run_invoice(item["path"], extraction=extraction_for(item, mode))
    if mode == "live" and result.get("extracted"):
        item["cache"].parent.mkdir(parents=True, exist_ok=True)
        item["cache"].write_text(json.dumps({"scenario": item["scenario"], **result.get("extraction", {}),
                                             "data": result["extracted"]}, indent=2), encoding="utf-8")
    return result


def main(set_name: str, mode: str, only: list[str]) -> None:
    items = [i for i in sample_files() if i["set"] == set_name and (not only or i["scenario"] in only)]
    by_id = {i["scenario"]: i for i in sample_files()}
    config.STAGE_PAUSE_S = 0
    rows, field_totals, field_runs = [], {}, 0
    for item in items:
        tmp = Path(tempfile.mkdtemp())
        config.STORAGE_DIR, config.DB_PATH = tmp, tmp / "eval.db"
        db.reset()
        result = run_item(item, mode, by_id)
        decision = result["decision"]
        ok, why = judge(item["expected"], decision)
        misses = []
        if mode != "truth" and result.get("extracted"):
            checks = score(result["extracted"], item["ground_truth"])
            field_runs += 1
            for name, good in checks.items():
                field_totals[name] = field_totals.get(name, 0) + good
            misses = [n for n, good in checks.items() if not good]
        model = (result.get("extraction") or {}).get("model", "-")
        rows.append({"scenario": item["scenario"], "title": item["title"], "expected": item["expected"]["decision"],
                     "got": decision["outcome"], "owner": decision["owner"], "reasons": decision["reasons"],
                     "correct": ok, "why": why, "field_misses": misses, "model": model, "seconds": result["seconds"],
                     "summary": decision["summary"]})
        print(f"{'PASS' if ok else 'FAIL'}  {item['scenario']:6} expected {item['expected']['decision']:17} "
              f"got {decision['outcome']:17} {','.join(decision['reasons']) or '-':18} {result['seconds']:6.1f}s  "
              f"{why if not ok else ''}{'  fields missed: ' + ','.join(misses) if misses else ''}")
    correct = sum(r["correct"] for r in rows)
    print(f"\nDecisions correct: {correct}/{len(rows)}")
    if field_runs:
        print("Field accuracy: " + "  ".join(f"{k} {v}/{field_runs}" for k, v in field_totals.items()))
    report = {"set": set_name, "mode": mode, "at": datetime.now(timezone.utc).isoformat(timespec="seconds"),
              "decisions_correct": correct, "total": len(rows), "field_accuracy": field_totals,
              "field_runs": field_runs, "rows": rows}
    if not only:    # partial runs are for spot checks; only full runs replace the saved report
        out = ROOT / "samples" / ("holdout" if set_name == "holdout" else "")
        (out / f"report_{mode}.json").write_text(json.dumps(report, indent=2), encoding="utf-8")


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "holdout", sys.argv[2] if len(sys.argv) > 2 else "truth", sys.argv[3:])
