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
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")


def _models(name: str, default: str) -> list[str]:
    """Model lists are tried in order; a busy model is skipped for the next (free-tier capacity varies)."""
    return [m.strip() for m in os.getenv(name, default).split(",") if m.strip()]


GROQ_MODELS = _models("GROQ_MODELS", "openai/gpt-oss-120b,openai/gpt-oss-20b")
GEMINI_MODELS = _models("GEMINI_MODELS", "gemini-3.6-flash,gemini-3.5-flash-lite,gemini-flash-lite-latest")

_WINDOWS_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or (_WINDOWS_TESSERACT if os.name == "nt" else "tesseract")

POLICY: dict = yaml.safe_load((ROOT / "policy.yaml").read_text(encoding="utf-8"))
