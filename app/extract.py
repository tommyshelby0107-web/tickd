"""Turn page text into structured invoice fields - with plain Python when it can prove the result, AI when it can't.

Order: 1) Python parser (no AI): accepted only if every line and total reconciles.
       2) Qwen on Groq (fast, text only).   3) Gemini (also reads page images).
       4) Mistral (also reads page images; a different company, so a Gemini outage does not stop scans).   5) a human.
Whichever reads the invoice, it only reads. Every decision is made by the rules in rules.py.
"""
import base64
import copy
import re
import time
from dataclasses import dataclass
from pathlib import Path

import groq
import httpx
from google import genai
from google.genai import errors, types
from mistralai.client import Mistral
from mistralai.client import errors as mistral_errors
from mistralai.client.utils.retries import RetryConfig
from pydantic import BaseModel, ValidationError

from .config import (GEMINI_API_KEY, GEMINI_MODELS, GROQ_API_KEY, GROQ_MODELS, MISTRAL_API_KEY, MISTRAL_MODELS, POLICY,
                     PROVIDER_ORDER)
from .normalize import currency_code, detect_currency
from .parser import parse_invoice
from .schema import InvoiceData, LineItem, Sourced  # noqa: F401  (re-exported for the rest of the app)
from .text import PageText, as_prompt_text, page_jpeg

SYSTEM_PROMPT = """You extract data from vendor invoices for an accounts payable team.

Rules:
- Use only what is printed in the page text. Never invent, infer or calculate a value that is not printed.
- If a field is not printed, return null for it.
- If a purchase order number is printed (labels such as PO, P.O. #, Your PO, Customer PO, Purchase Order),
  put it in po_number.value. Never guess one. Put order reference wording without a number in po_hint.
- invoice_number: exactly as printed, including spaces and hyphens. It may be labelled Invoice #, Invoice No.,
  Invoice Number, Bill Number, Bill No., Document No. or Reference No.
- tax_included_in_prices: true when the invoice says the prices or the total include tax (e.g. "Total (includes
  7.5% sales tax of $138.60)"); then the tax is already inside the line amounts.
- Dates: value as YYYY-MM-DD; source_quote as printed.
- Money: plain numbers with no currency symbols or thousands separators. Keep minus signs as printed.
- currency: the ISO code of the printed currency, never converted: USD for $, INR for Rs or ₹, EUR for €,
  GBP for £. Null if no currency is printed.
- document_type: "credit_note" if the document is a credit note or credit memo, "other" if it is not a bill
  (statement, quote, reminder), otherwise "invoice".
- source_quote: a short snippet copied character-for-character from the page text, e.g. "Invoice No. INV-2026-0457".
- Page text may come from OCR and contain small errors. Read carefully and keep printed values as they are."""

PARSER = "Python parser (no AI)"
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
    image_pages: list[int]      # pages sent to the AI as images because OCR confidence was low
    fallbacks: list[str]        # why earlier readers were not used (parser checks, busy models)


def extract_invoice(pdf_path: Path, pages: list[PageText]) -> Extraction:
    started, skipped = time.perf_counter(), []

    # 1) Plain Python first - digital PDFs, and scans that OCR read with high confidence.
    min_ocr = POLICY["parser_ocr_confidence_min"]
    if all(p.source == "text-layer" or (p.ocr_confidence or 0) >= min_ocr for p in pages):
        data, reasons = parse_invoice(pages)
        if data:
            return Extraction(data, PARSER, round(time.perf_counter() - started, 2), 0, 0, [], [])
        skipped.append("Python parser could not prove the reading: " + "; ".join(reasons))
    else:
        skipped.append(f"Python parser skipped: OCR confidence below {min_ocr}%")

    # 2) to 4) AI. Pages OCR could barely read are sent as images; everything else is text.
    prompt = f"Extract the invoice fields from this document.\n\n{as_prompt_text(pages)}"
    image_pages = [p.number for p in pages
                   if p.source == "ocr" and (p.ocr_confidence or 0) < POLICY["ocr_image_fallback_below"]]
    available = {
        "groq": _groq if GROQ_API_KEY and not image_pages else None,   # Qwen reads text only
        "gemini": _gemini if GEMINI_API_KEY else None,                  # Gemini also reads page images
        "mistral": _mistral if MISTRAL_API_KEY else None,               # so does Mistral
    }
    providers = [available[name] for name in PROVIDER_ORDER if available.get(name)]
    if not providers:
        raise ExtractionError(" | ".join(skipped + ["no AI reader configured for this document"]))
    for provider in providers:
        try:
            data, model, tokens_in, tokens_out = provider(prompt, pdf_path, image_pages, skipped)
        except ExtractionError as exc:
            skipped.append(str(exc))
            continue
        _recover_printed_po(data)
        _recover_printed_total(data)
        _infer_tax_included(data)
        _strip_number_label(data)
        _printed_currency(data, pages)
        return Extraction(data, model, round(time.perf_counter() - started, 2), tokens_in, tokens_out,
                          image_pages, skipped)
    raise ExtractionError(" | ".join(skipped))      # 4) the pipeline turns this into a human review


# ---------------------------------------------------------------- Qwen on Groq (fast, text only)

def _groq(prompt: str, pdf_path: Path, image_pages: list[int], skipped: list[str]):
    client = groq.Groq(api_key=GROQ_API_KEY, timeout=CALL_TIMEOUT_S, max_retries=0)
    for model in GROQ_MODELS:
        extra = {"reasoning_effort": "low"} if "gpt-oss" in model else {}   # only gpt-oss takes this setting
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": prompt}],
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "invoice", "strict": True, "schema": STRICT_SCHEMA}},
                temperature=0,
                **extra,
            )
            data = InvoiceData.model_validate_json(response.choices[0].message.content)
            return data, model, response.usage.prompt_tokens, response.usage.completion_tokens
        except groq.APIStatusError as exc:
            schema_miss = exc.status_code == 400 and "json_validate_failed" in str(exc.body)
            if exc.status_code not in BUSY and not schema_miss:
                raise ExtractionError(f"Groq {model} failed ({exc.status_code}): {exc.message}") from exc
            where = re.search(r"jsonschema: '([^']*)'", str(exc.body))      # which field broke the schema
            skipped.append(f"{model}: " + (f"output did not match the schema at {where.group(1) if where else '?'}"
                                           if schema_miss else f"busy ({exc.status_code})"))
        except (groq.APIConnectionError, ValidationError) as exc:          # timeouts, network, malformed output
            skipped.append(f"{model}: {type(exc).__name__}")
    raise ExtractionError("Qwen unavailable")


def _strict_schema(model: type[BaseModel]) -> dict:
    """Strict mode (Groq, Mistral) wants every object closed (additionalProperties false), every field required, no $refs."""
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
    contents: list = [prompt] + [types.Part.from_bytes(data=page_jpeg(pdf_path, n), mime_type="image/jpeg")
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
    raise ExtractionError("Gemini unavailable")


# ---------------------------------------------------------------- Mistral (second image reader, another company)

def _mistral(prompt: str, pdf_path: Path, image_pages: list[int], skipped: list[str]):
    content: list = [{"type": "text", "text": prompt}] + [
        {"type": "image_url",
         "image_url": {"url": "data:image/jpeg;base64," + base64.b64encode(page_jpeg(pdf_path, n)).decode()}}
        for n in image_pages]
    client = Mistral(api_key=MISTRAL_API_KEY, timeout_ms=CALL_TIMEOUT_S * 1000)
    for model in MISTRAL_MODELS:
        try:
            response = client.chat.complete(
                model=model,
                messages=[{"role": "system", "content": SYSTEM_PROMPT}, {"role": "user", "content": content}],
                response_format={"type": "json_schema",
                                 "json_schema": {"name": "invoice", "schema": STRICT_SCHEMA, "strict": True}},
                temperature=0,
                retries=RetryConfig("none", None, False),          # no hidden waits: busy means next reader
            )
            data = InvoiceData.model_validate_json(response.choices[0].message.content)
            return data, model, response.usage.prompt_tokens or 0, response.usage.completion_tokens or 0
        except mistral_errors.MistralError as exc:
            if exc.status_code not in BUSY:
                raise ExtractionError(f"Mistral {model} failed ({exc.status_code}): {exc.message[:120]}") from exc
            skipped.append(f"{model}: busy ({exc.status_code})")
        except (httpx.HTTPError, mistral_errors.NoResponseError, ValidationError) as exc:   # timeouts, bad output
            skipped.append(f"{model}: {type(exc).__name__}")
    raise ExtractionError("Mistral unavailable")


# ---------------------------------------------------------------- deterministic clean-up of AI readings

PRINTED_PO = re.compile(r"\bP\.?\s?O\.?\s*(?:number|no\.?|#)?\s*[:#-]?\s*((?:PO-?)?\d{3,})", re.IGNORECASE)
NUMBER_LABEL = re.compile(r"(?:\bno\.?|\bnumber|#)\s*[:.]?\s*([A-Za-z0-9][\w\-/]*(?:[ ][\w\-/]+)*)\s*$", re.IGNORECASE)
PRINTED_AMOUNT = re.compile(r"(-?)\$?\s*(-?)(\d[\d,]*\.\d{2})")


def _printed_currency(data: InvoiceData, pages: list[PageText]) -> None:
    """The currency printed on the page ('Rs 564.00' -> INR) wins over the model's answer; the model's answer is
    used when the page text shows none (e.g. a photo OCR could barely read). Amounts are never converted."""
    data.currency = detect_currency("\n".join(p.text for p in pages)) or currency_code(data.currency)


def _strip_number_label(data: InvoiceData) -> None:
    """OCR can merge columns, so a model may return 'Accounts Payable No. NLS-7781' as the invoice number.
    If the value still contains a label (No., Number, #), keep only the identifier after the last one."""
    value = data.invoice_number.value
    if value and " " in value:
        match = NUMBER_LABEL.search(value)
        if match and match.group(1) != value:
            data.invoice_number.value = match.group(1)


def _infer_tax_included(data: InvoiceData) -> None:
    """Arithmetic, not guessing: if the lines (plus freight) already add up to the total while tax is stated
    separately, the tax must be inside the line prices."""
    try:
        total = float(data.total.value) if data.total.value else None
    except ValueError:
        return
    if data.tax_included_in_prices or not data.tax_amount or total is None or not data.lines:
        return
    lines_plus_freight = sum(l.amount for l in data.lines) + (data.freight or 0)
    if abs(lines_plus_freight - total) <= 0.01 and abs(lines_plus_freight + data.tax_amount - total) > 0.01:
        data.tax_included_in_prices = True


def _recover_printed_total(data: InvoiceData) -> None:
    """If the model quoted the printed total (e.g. 'TOTAL $5,565.00') but left the value empty, take it from the quote.
    Safe because the quote itself is verified against the page text later (rule V-05)."""
    if data.total.value or not data.total.source_quote:
        return
    amounts = PRINTED_AMOUNT.findall(data.total.source_quote)
    if amounts:
        sign_a, sign_b, number = amounts[-1]
        data.total.value = ("-" if (sign_a or sign_b) else "") + number.replace(",", "")


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
