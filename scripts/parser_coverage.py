"""Which sample invoices can the Python parser read without AI, how fast, and are its readings right?

Run:  python scripts/parser_coverage.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "scripts")]

from app.config import POLICY  # noqa: E402
from app.parser import parse_invoice  # noqa: E402
from app.pipeline import sample_files  # noqa: E402
from app.text import read_pages  # noqa: E402
from check_extraction import score  # noqa: E402

accepted = 0
items = sample_files()
for item in items:
    pages = read_pages(item["path"])
    low_ocr = [p for p in pages if p.source == "ocr" and (p.ocr_confidence or 0) < POLICY["parser_ocr_confidence_min"]]
    started = time.perf_counter()
    data, reasons = (None, ["OCR confidence below the parser threshold"]) if low_ocr else parse_invoice(pages)
    ms = (time.perf_counter() - started) * 1000
    if data:
        accepted += 1
        misses = [k for k, v in score(data.model_dump(), item["ground_truth"]).items() if not v]
        print(f"PYTHON {item['scenario']:6} {item['layout']:8} {ms:5.0f} ms  {'ALL FIELDS RIGHT' if not misses else 'WRONG: ' + ','.join(misses)}")
    else:
        print(f"-> AI  {item['scenario']:6} {item['layout']:8} {ms:5.0f} ms  {'; '.join(reasons)}")
print(f"\nPython parser read {accepted} of {len(items)} invoices without AI.")
