"""Paths, secrets and the approval policy, loaded once at startup."""
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
load_dotenv(ROOT / ".env")

DATA_DIR = ROOT / "data"
SAMPLES_DIR = ROOT / "samples"
STORAGE_DIR = Path(os.getenv("STORAGE_DIR", str(ROOT / "storage")))
DB_PATH = STORAGE_DIR / "invoice_agent.db"

GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.5-flash")

_WINDOWS_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or (_WINDOWS_TESSERACT if os.name == "nt" else "tesseract")

POLICY: dict = yaml.safe_load((ROOT / "policy.yaml").read_text(encoding="utf-8"))
