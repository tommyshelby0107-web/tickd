"""Turn page text into structured invoice fields with an LLM (Gemini, free tier).

The LLM only reads. It never decides: every decision is made by the rules in rules.py.
"""
import re
import time
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

from .config import GEMINI_API_KEY, GEMINI_MODELS, POLICY
from .text import PageText, as_prompt_text, page_png


class Sourced(BaseModel):
    """A critical field plus the evidence for it, so code can check the LLM did not invent it."""
    value: str | None = Field(description="The value, or null if it is not printed on the invoice")
    page: int | None = Field(description="Page number the value was found on")
    source_quote: str | None = Field(
        description="Short snippet copied verbatim from the page text that contains the value")


class LineItem(BaseModel):
    sku: str | None = Field(description="Item code / part number / SKU if printed, else null")
    description: str
    quantity: float
    unit_price: float
    amount: float


class InvoiceData(BaseModel):
    vendor_name: Sourced
    vendor_tax_id: str | None = Field(description="EIN / Fed Tax ID if printed")
    invoice_number: Sourced = Field(description="value exactly as printed, keeping spaces and hyphens")
    invoice_date: Sourced = Field(description="value in YYYY-MM-DD format")
    due_date: str | None = Field(description="YYYY-MM-DD, only if printed")
    currency: str | None = Field(description="ISO code such as USD")
    po_number: Sourced = Field(description="Only a purchase order number actually printed; never guess one")
    po_hint: str | None = Field(
        description="Any wording that might identify the order when no PO number is printed, e.g. 'Re: Q3 order'")
    lines: list[LineItem]
    subtotal: float | None
    tax_amount: float | None
    tax_rate_pct: float | None = Field(description="Tax rate in percent, e.g. 7.5 for 7.5%")
    tax_included_in_prices: bool = Field(description="True only if the invoice says prices include tax")
    freight: float | None = Field(description="Freight, shipping or delivery charge, if any")
    total: Sourced = Field(description="Amount due, as a plain number")
    remit_bank_name: str | None
    remit_routing_number: Sourced
    remit_account_number: Sourced
    notes: str | None = Field(description="Any payment notice or instruction printed on the invoice, verbatim")


SYSTEM_PROMPT = """You extract data from vendor invoices for an accounts payable team.

Rules:
- Use only what is printed in the page text. Never invent, infer or calculate a value that is not printed.
- If a field is not printed, return null for it.
- If a purchase order number is printed (labels such as PO, P.O. #, Your PO, Customer PO, Purchase Order),
  put it in po_number.value. Never guess one. Put order reference wording without a number in po_hint.
- invoice_number: exactly as printed, including spaces and hyphens.
- Dates: value as YYYY-MM-DD; source_quote as printed.
- Money: plain numbers with no currency symbols or thousands separators.
- source_quote: a short snippet copied character-for-character from the page text, e.g. "Invoice No. INV-2026-0457".
- Page text may come from OCR and contain small errors. Read carefully and keep printed values as they are."""


class ExtractionError(Exception):
    pass


@dataclass
class Extraction:
    data: InvoiceData
    model: str
    seconds: float
    input_tokens: int
    output_tokens: int
    image_pages: list[int]      # pages also sent as images because OCR confidence was low


def extract_invoice(pdf_path: Path, pages: list[PageText]) -> Extraction:
    if not GEMINI_API_KEY:
        raise ExtractionError("GEMINI_API_KEY is not set in .env")
    contents: list = [f"Extract the invoice fields from this document.\n\n{as_prompt_text(pages)}"]
    image_pages = [p.number for p in pages
                   if p.source == "ocr" and (p.ocr_confidence or 0) < POLICY["ocr_image_fallback_below"]]
    for number in image_pages:
        contents.append(types.Part.from_bytes(data=page_png(pdf_path, number, dpi=200), mime_type="image/png"))

    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=InvoiceData,
        temperature=0,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    client = genai.Client(api_key=GEMINI_API_KEY,
                          http_options=types.HttpOptions(timeout=CALL_TIMEOUT_MS, retry_options=types.HttpRetryOptions(attempts=1)))
    started = time.perf_counter()
    response, model = _generate_with_fallback(client, contents, config)
    data = response.parsed if isinstance(response.parsed, InvoiceData) else InvoiceData.model_validate_json(response.text)
    _recover_printed_po(data)
    usage = response.usage_metadata
    return Extraction(
        data=data,
        model=model,
        seconds=round(time.perf_counter() - started, 2),
        input_tokens=(usage.prompt_token_count or 0) if usage else 0,
        output_tokens=(usage.candidates_token_count or 0) if usage else 0,
        image_pages=image_pages,
    )


PRINTED_PO = re.compile(r"\bP\.?\s?O\.?\s*(?:number|no\.?|#)?\s*[:#-]?\s*((?:PO-?)?\d{3,})", re.IGNORECASE)


def _recover_printed_po(data: InvoiceData) -> None:
    """Deterministic clean-up: if the model quoted a printed PO number but left the value empty, use it."""
    if data.po_number.value:
        return
    for text in (data.po_number.source_quote, data.po_hint):
        match = PRINTED_PO.search(text or "")
        if match:
            data.po_number.value = match.group(1)
            data.po_number.source_quote = data.po_number.source_quote or text
            return


CALL_TIMEOUT_MS = 60_000
BUSY = (429, 500, 503, 504)


def _generate_with_fallback(client: genai.Client, contents: list, config: types.GenerateContentConfig):
    """Try each model in GEMINI_MODELS in order. A busy model is skipped at once rather than waited on;
    after one full pass, wait briefly and make a second pass before giving up."""
    failures = []
    for attempt in range(2):
        for model in GEMINI_MODELS:
            try:
                return client.models.generate_content(model=model, contents=contents, config=config), model
            except errors.APIError as exc:
                failures.append(f"{model}: {exc.code}")
                if exc.code not in BUSY:
                    raise ExtractionError(f"Gemini call failed on {model} ({exc.code}): {exc.message}") from exc
        if attempt == 0:
            time.sleep(5)
    raise ExtractionError("All Gemini models busy: " + ", ".join(failures))
