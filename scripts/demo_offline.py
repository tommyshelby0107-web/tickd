"""Run every scenario through the full pipeline without the LLM, using ground-truth extraction.

Useful to check the rules and messages quickly, and as a fallback if the LLM is unavailable.
Run:  python scripts/demo_offline.py
"""
import sys
import tempfile
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT), str(ROOT / "tests")]

from app import config, db  # noqa: E402

config.STORAGE_DIR = Path(tempfile.mkdtemp())
config.DB_PATH = config.STORAGE_DIR / "offline.db"
db.reset()

from conftest import sample  # noqa: E402
from app.pipeline import run_invoice  # noqa: E402

for scenario in ["HP-1", "HP-2", "EC-1B", "EC-2", "EC-3", "EC-4", "RV-1", "X-1", "X-2"]:
    pdf, extraction = sample(scenario)
    result = run_invoice(pdf, extraction=extraction)
    d = result["decision"]
    print(f"--- {scenario}: {d['outcome']} | owner={d['owner']} | severity={d['severity']} | reasons={d['reasons']}")
    print(f"    {d['summary']}")
    print(f"    next: {d['next_action']}")
    if result.get("po_candidates"):
        print(f"    PO candidates: {result['po_candidates']}")
