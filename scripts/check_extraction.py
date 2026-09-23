"""Run text reading + LLM extraction on every sample and score it against the manifest's ground truth.

Saves each extraction to samples/extracted/<scenario>.json so later stages can be tested without API calls.

Run:  python scripts/check_extraction.py            (all samples)
      python scripts/check_extraction.py EC-3 HP-1  (selected scenarios)
"""
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.config import SAMPLES_DIR  # noqa: E402
from app.extract import extract_invoice  # noqa: E402
from app.text import read_pages  # noqa: E402

CACHE = SAMPLES_DIR / "extracted"


def as_float(value) -> float | None:
    if value in (None, ""):
        return None
    return float(str(value).replace(",", "").replace("$", ""))


def same_money(a, b) -> bool:
    a, b = as_float(a) or 0.0, as_float(b) or 0.0
    return abs(a - b) < 0.005


def score(data: dict, truth: dict) -> dict[str, bool]:
    lines_ok = len(data["lines"]) == len(truth["lines"]) and all(
        abs(l["quantity"] - float(t["qty"])) < 1e-9 and same_money(l["unit_price"], t["unit_price"])
        for l, t in zip(data["lines"], truth["lines"]))
    return {
        "number": data["invoice_number"]["value"] == truth["invoice_number_as_printed"],
        "date": data["invoice_date"]["value"] == truth["invoice_date"],
        "po": data["po_number"]["value"] == truth["po_number"],
        "lines": lines_ok,
        "subtotal": same_money(data["subtotal"], truth["subtotal"]),
        "tax": same_money(data["tax_amount"], truth["tax"]),
        "freight": same_money(data["freight"], truth["freight"]),
        "total": same_money(data["total"]["value"], truth["total"]),
        "account": data["remit_account_number"]["value"] == truth["remit_account"],
    }


def main(selected: list[str]) -> None:
    manifest = json.loads((SAMPLES_DIR / "manifest.json").read_text(encoding="utf-8"))
    CACHE.mkdir(exist_ok=True)
    totals: dict[str, int] = {}
    runs = 0
    for item in manifest:
        if selected and item["scenario"] not in selected:
            continue
        pdf = SAMPLES_DIR / "invoices" / item["file"]
        pages = read_pages(pdf)
        result = extract_invoice(pdf, pages)
        data = result.data.model_dump()
        (CACHE / f"{item['scenario']}.json").write_text(json.dumps({
            "scenario": item["scenario"], "model": result.model, "seconds": result.seconds,
            "input_tokens": result.input_tokens, "output_tokens": result.output_tokens,
            "pages": [{"number": p.number, "source": p.source, "ocr_confidence": p.ocr_confidence} for p in pages],
            "data": data,
        }, indent=2), encoding="utf-8")
        checks = score(data, item["ground_truth"])
        runs += 1
        for name, ok in checks.items():
            totals[name] = totals.get(name, 0) + ok
        misses = [name for name, ok in checks.items() if not ok]
        status = "OK  " if not misses else "MISS"
        print(f"{status} {item['scenario']:6} {pages[0].source:10} {result.seconds:5.1f}s "
              f"{result.input_tokens:5}+{result.output_tokens:<5} tok  {', '.join(misses)}")
    if runs:
        print("\nField accuracy: " + "  ".join(f"{k} {v}/{runs}" for k, v in totals.items()))


if __name__ == "__main__":
    main(sys.argv[1:])
