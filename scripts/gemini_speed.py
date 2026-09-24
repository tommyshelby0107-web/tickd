"""How fast is each free Gemini model, with thinking at its default vs MINIMAL? Same digital invoice, same prompt.

Run:  python scripts/gemini_speed.py
"""
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from google import genai  # noqa: E402
from google.genai import errors, types  # noqa: E402

from app.config import GEMINI_API_KEY, SAMPLES_DIR  # noqa: E402
from app.extract import SYSTEM_PROMPT, InvoiceData  # noqa: E402
from app.text import as_prompt_text, read_pages  # noqa: E402

MODELS = ["gemini-3.5-flash-lite", "gemini-3.1-flash-lite", "gemini-flash-lite-latest", "gemini-3.5-flash"]
pages = read_pages(SAMPLES_DIR / "invoices" / "HP-2_coastal_CPK-88214.pdf")
prompt = f"Extract the invoice fields from this document.\n\n{as_prompt_text(pages)}"
client = genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(
    timeout=90_000, retry_options=types.HttpRetryOptions(attempts=1)))

for model in MODELS:
    for level in (None, types.ThinkingLevel.MINIMAL):
        config = types.GenerateContentConfig(
            system_instruction=SYSTEM_PROMPT, response_mime_type="application/json", response_schema=InvoiceData,
            temperature=0, automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
            thinking_config=types.ThinkingConfig(thinking_level=level) if level else None)
        started = time.perf_counter()
        try:
            r = client.models.generate_content(model=model, contents=[prompt], config=config)
            data = r.parsed if isinstance(r.parsed, InvoiceData) else InvoiceData.model_validate_json(r.text)
            u = r.usage_metadata
            print(f"{model:26} thinking={'default' if level is None else 'MINIMAL':8} {time.perf_counter() - started:5.1f}s "
                  f"thought tokens={u.thoughts_token_count or 0:<5} output={u.candidates_token_count or 0:<5} "
                  f"number={data.invoice_number.value} total={data.total.value}", flush=True)
        except errors.APIError as e:
            print(f"{model:26} thinking={'default' if level is None else 'MINIMAL':8} {time.perf_counter() - started:5.1f}s "
                  f"ERROR {e.code}: {(e.message or '')[:90]}", flush=True)
        except Exception as e:
            print(f"{model:26} thinking={'default' if level is None else 'MINIMAL':8} ERROR {type(e).__name__}: {str(e)[:90]}")
