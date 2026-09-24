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


# Defaults follow the head-to-head benchmark (scripts/compare_llms.py): accuracy first, then speed.
PROVIDER_ORDER = _models("LLM_PROVIDER_ORDER", "gemini,groq")   # which provider is tried first
GROQ_MODELS = _models("GROQ_MODELS", "qwen/qwen3.8-27b,openai/gpt-oss-120b")
GEMINI_MODELS = _models("GEMINI_MODELS", "gemini-3.5-flash-lite,gemini-3.6-flash")

_WINDOWS_TESSERACT = r"C:\Program Files\Tesseract-OCR\tesseract.exe"
TESSERACT_CMD = os.getenv("TESSERACT_CMD") or (_WINDOWS_TESSERACT if os.name == "nt" else "tesseract")

# Email intake: a dedicated inbox polled over IMAP (Gmail: 2-Step Verification + an App Password).
EMAIL_ADDRESS = os.getenv("EMAIL_ADDRESS", "")
EMAIL_APP_PASSWORD = os.getenv("EMAIL_APP_PASSWORD", "").replace(" ", "")   # Gmail shows it in groups of four
EMAIL_IMAP_HOST = os.getenv("EMAIL_IMAP_HOST", "imap.gmail.com")
EMAIL_FOLDER = os.getenv("EMAIL_FOLDER", "INBOX")
EMAIL_POLL_SECONDS = int(os.getenv("EMAIL_POLL_SECONDS", "20"))
# Staff addresses that forward vendor invoices into the inbox: the sender check cannot judge the original sender.
EMAIL_TRUSTED_FORWARDERS = [a.strip().lower() for a in os.getenv("EMAIL_TRUSTED_FORWARDERS", "").split(",") if a.strip()]


def email_enabled() -> bool:
    return bool(EMAIL_ADDRESS and EMAIL_APP_PASSWORD)


def uploads_dir() -> Path:
    """Where every received PDF is kept, one folder per run."""
    return STORAGE_DIR / "uploads"


# Pause between rule stages so people watching the live view can follow it (0 in tests).
STAGE_PAUSE_S = float(os.getenv("STAGE_PAUSE_S", "0.4"))
# "live" calls the LLM; "cached" reuses samples/extracted/*.json for known sample files (clearly labelled).
EXTRACTION_MODE = os.getenv("EXTRACTION_MODE", "live")

POLICY: dict = yaml.safe_load((ROOT / "policy.yaml").read_text(encoding="utf-8"))
