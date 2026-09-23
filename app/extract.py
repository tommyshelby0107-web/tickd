"""Turn page text into structured invoice fields with an LLM.

Providers are tried in order: Groq (fast, free tier) then Gemini (free tier, also reads page images).
The LLM only reads. It never decides: every decision is made by the rules in rules.py.
"""
import copy
import re
import time
from dataclasses import dataclass
from pathlib import Path

import groq
from google import genai
from google.genai import errors, types
from pydantic import BaseModel, Field, ValidationError

from .config import GEMINI_API_KEY, GEMINI_MODELS, GROQ_API_KEY, GROQ_MODELS, POLICY
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

CALL_TIMEOUT_S = 45
BUSY = (429, 500, 502, 503, 504)


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
    fallbacks: list[str]        # providers/models skipped before one answered


def extract_invoice(pdf_path: Path, pages: list[PageText]) -> Extraction:
    prompt = f"Extract the invoice fields from this document.\n\n{as_prompt_text(pages)}"
    image_pages = [p.number for p in pages
                   if p.source == "ocr" and (p.ocr_confidence or 0) < POLICY["ocr_image_fallback_below"]]
    providers = []
    if GROQ_API_KEY and not image_pages:     # the Groq models we use read text only; image pages need Gemini
        providers.append(_groq)
    if GEMINI_API_KEY:
        providers.append(_gemini)
    if not providers:
        raise ExtractionError("No LLM key configured: set GROQ_API_KEY or GEMINI_API_KEY in .env")

    started, skipped = time.perf_counter(), []
    for provider in providers:
        try:
            data, model, tokens_in, tokens_out = provider(prompt, pdf_path, image_pages, skipped)
        except ExtractionError as exc:
            skipped.append(str(exc))
            continue
        _recover_printed_po(data)
        return Extraction(data, model, round(time.perf_counter() - started, 2), tokens_in, tokens_out,
                          image_pages, skipped)
    raise ExtractionError(" | ".join(skipped))


# ---------------------------------------------------------------- Groq (primary)

def _groq(prompt: str, pdf_path: Path, image_pages: list[int], skipped: list[str]):
    client = groq.Groq(api_key=GROQ_API_KEY, timeout=CALL_TIMEOUT_S, max_retries=0)
    for model in GROQ_MODELS:
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "invoice", "strict": True, "schema": STRICT_SCHEMA}},
                temperature=0,
                reasoning_effort="low",
            )
            data = InvoiceData.model_validate_json(response.choices[0].message.content)
        except groq.APIStatusError as exc:
            if exc.status_code not in BUSY:
                raise ExtractionError(f"Groq {model} failed ({exc.status_code}): {exc.message}") from exc
            skipped.append(f"{model}: busy ({exc.status_code})")
            continue
        except (groq.APIConnectionError, ValidationError) as exc:     # timeouts, network, malformed output
            skipped.append(f"{model}: {type(exc).__name__}")
            continue
        return data, model, response.usage.prompt_tokens, response.usage.completion_tokens
    raise ExtractionError("All Groq models unavailable")


def _strict_schema(model: type[BaseModel]) -> dict:
    """Groq strict mode wants every object closed (additionalProperties false), every field required, no $refs."""
    schema = model.model_json_schema()
    defs = schema.pop("$defs", {})

    def fix(node):
        if isinstance(node, list):
            return [fix(n) for n in node]
        if not isinstance(node, dict):
            return node
        if "$ref" in node:
            resolved = fix(copy.deepcopy(defs[node["$ref"].split("/")[-1]]))
            if "description" in node:
                resolved["description"] = node["description"]
            return resolved
        out = {k: (fix(v) if k != "properties" else {name: fix(p) for name, p in v.items()})
               for k, v in node.items() if k not in ("title", "default")}
        if out.get("type") == "object":
            out["additionalProperties"] = False
            out["required"] = list(out.get("properties", {}))
        return out

    return fix(schema)


STRICT_SCHEMA = _strict_schema(InvoiceData)


# ---------------------------------------------------------------- Gemini (backup; also reads page images)

def _gemini(prompt: str, pdf_path: Path, image_pages: list[int], skipped: list[str]):
    contents: list = [prompt] + [types.Part.from_bytes(data=page_png(pdf_path, n, dpi=200), mime_type="image/png")
                                 for n in image_pages]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        response_mime_type="application/json",
        response_schema=InvoiceData,
        temperature=0,
        automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
    )
    client = genai.Client(api_key=GEMINI_API_KEY, http_options=types.HttpOptions(
        timeout=CALL_TIMEOUT_S * 1000, retry_options=types.HttpRetryOptions(attempts=1)))
    for model in GEMINI_MODELS:
        try:
            response = client.models.generate_content(model=model, contents=contents, config=config)
        except errors.APIError as exc:
            if exc.code not in BUSY:
                raise ExtractionError(f"Gemini {model} failed ({exc.code}): {exc.message}") from exc
            skipped.append(f"{model}: busy ({exc.code})")
            continue
        data = response.parsed if isinstance(response.parsed, InvoiceData) else InvoiceData.model_validate_json(response.text)
        usage = response.usage_metadata
        return (data, model, (usage.prompt_token_count or 0) if usage else 0,
                (usage.candidates_token_count or 0) if usage else 0)
    raise ExtractionError("All Gemini models busy")


# ---------------------------------------------------------------- deterministic clean-up

PRINTED_PO = re.compile(r"\bP\.?\s?O\.?\s*(?:number|no\.?|#)?\s*[:#-]?\s*((?:PO-?)?\d{3,})", re.IGNORECASE)


def _recover_printed_po(data: InvoiceData) -> None:
    """If the model quoted a printed PO number but left the value empty, use it."""
    if data.po_number.value:
        return
    for text in (data.po_number.source_quote, data.po_hint):
        match = PRINTED_PO.search(text or "")
        if match:
            data.po_number.value = match.group(1)
            data.po_number.source_quote = data.po_number.source_quote or text
            return
