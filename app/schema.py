"""The invoice fields every reader must produce: the Python parser, Qwen (Groq) and Gemini all fill this schema."""
from pydantic import BaseModel, Field, model_validator


class Sourced(BaseModel):
    """A critical field plus the evidence for it, so code can check it was not invented."""
    value: str | None = Field(description="The value, or null if it is not printed on the invoice")
    page: int | None = Field(description="Page number the value was found on")
    source_quote: str | None = Field(
        description="Short snippet copied verbatim from the page text that contains the value")

    @model_validator(mode="before")
    @classmethod
    def _plain_value(cls, data):
        """Accept a bare value too (older saved extractions store some fields that way)."""
        if data is None or isinstance(data, (str, int, float)):
            return {"value": None if data is None else str(data), "page": None, "source_quote": None}
        return data


class LineItem(BaseModel):
    sku: str | None = Field(description="Item code / part number / SKU if printed, else null")
    description: str
    quantity: float
    unit_price: float
    amount: float


class InvoiceData(BaseModel):
    document_type: str = Field("invoice", description="invoice, credit_note, or other (statement, quote, reminder)")
    vendor_name: Sourced
    vendor_tax_id: str | None = Field(description="EIN / Fed Tax ID if printed")
    invoice_number: Sourced = Field(description="value exactly as printed, keeping spaces and hyphens")
    invoice_date: Sourced = Field(description="value in YYYY-MM-DD format")
    due_date: Sourced = Field(description="value in YYYY-MM-DD format, only if printed")
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
