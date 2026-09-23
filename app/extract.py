"""Turn page text into structured invoice fields with an LLM (Gemini, free tier).

The LLM only reads. It never decides: every decision is made by the rules in rules.py.
"""
import time
from dataclasses import dataclass
from pathlib import Path

from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field

from .config import GEMINI_API_KEY, GEMINI_MODEL, POLICY
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
- Never guess a purchase order number. Put any order reference wording in po_hint instead.
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
    )
    client = genai.Client(api_key=GEMINI_API_KEY)
    started = time.perf_counter()
    response = _generate_with_retry(client, contents, config)
    data = response.parsed if isinstance(response.parsed, InvoiceData) else InvoiceData.model_validate_json(response.text)
    usage = response.usage_metadata
    return Extraction(
        data=data,
        model=GEMINI_MODEL,
        seconds=round(time.perf_counter() - started, 2),
        input_tokens=(usage.prompt_token_count or 0) if usage else 0,
        output_tokens=(usage.candidates_token_count or 0) if usage else 0,
        image_pages=image_pages,
    )


def _generate_with_retry(client: genai.Client, contents: list, config: types.GenerateContentConfig, attempts: int = 3):
    """Retry rate limits and server errors with a short back-off; fail fast on anything else."""
    for attempt in range(1, attempts + 1):
        try:
            return client.models.generate_content(model=GEMINI_MODEL, contents=contents, config=config)
        except errors.APIError as exc:
            if attempt == attempts or exc.code not in (429, 500, 503):
                raise ExtractionError(f"Gemini call failed ({exc.code}): {exc.message}") from exc
            time.sleep(3 * attempt)
