"""Small helpers that turn messy printed values into comparable keys."""
import re
from collections import Counter
from datetime import date

from .config import POLICY

BASE_CURRENCY = POLICY["base_currency"]
SYMBOLS = {"USD": "$", "INR": "₹", "EUR": "€", "GBP": "£", "CAD": "C$", "AUD": "A$"}
PRINTED_CURRENCY = {        # how each currency shows up on an invoice
    "USD": r"\bUSD\b|US\$|(?<![A-Z])\$",
    "INR": r"\bINR\b|₹|\bRs\.?\s?(?=\d)|\bRupees?\b",
    "EUR": r"\bEUR\b|€",
    "GBP": r"\bGBP\b|£",
    "CAD": r"\bCAD\b|C\$",
    "AUD": r"\bAUD\b|A\$",
}


def detect_currency(text: str) -> str | None:
    """The currency printed most often on the page, e.g. 'Rs 564.00' -> 'INR'. None if no currency is printed."""
    counts = Counter({code: len(re.findall(pattern, text or "")) for code, pattern in PRINTED_CURRENCY.items()})
    code, n = counts.most_common(1)[0]
    return code if n else None


CURRENCY_ALIASES = {"$": "USD", "US$": "USD", "₹": "INR", "RS": "INR", "RS.": "INR", "RUPEE": "INR", "RUPEES": "INR",
                    "€": "EUR", "£": "GBP", "C$": "CAD", "A$": "AUD"}


def currency_code(value: str | None) -> str | None:
    """'Rs', '₹', 'inr' -> 'INR'; '$' -> 'USD'. Other three-letter codes are kept as they are."""
    value = (value or "").strip().upper()
    return CURRENCY_ALIASES.get(value) or (value if re.fullmatch(r"[A-Z]{3}", value) else None)


def invoice_key(number: str | None) -> str | None:
    """'INV-2026-0457', 'INV 2026 0457' and 'inv/2026/457' all become 'INV2026457'."""
    if not number or not number.strip():
        return None
    parts = [p for p in re.split(r"[\s\-/_.#]+", number.upper()) if p]
    return "".join((p.lstrip("0") or "0") if p.isdigit() else p for p in parts)


def po_key(number: str | None) -> str | None:
    """'PO-4501', 'PO 4501', 'P.O. #4501' and '4501' all become 'PO-4501'."""
    if not number:
        return None
    match = re.search(r"\d{3,}", number)
    return f"PO-{int(match.group())}" if match else None


def digits(value: str | None) -> str:
    return re.sub(r"\D", "", value or "")


def to_float(value) -> float | None:
    if value is None or str(value).strip() == "":
        return None
    try:
        return float(str(value).replace(",", "").replace("$", "").strip())
    except ValueError:
        return None


def parse_date(value: str | None) -> date | None:
    try:
        return date.fromisoformat(value) if value else None
    except ValueError:
        return None


def money(value: float | None, currency: str | None = None) -> str:
    """Format in the invoice's own currency: never converted. No currency printed means the base currency."""
    if value is None:
        return "n/a"
    code = currency or BASE_CURRENCY
    symbol = SYMBOLS.get(code)
    amount = f"{symbol}{abs(value):,.2f}" if symbol else f"{code} {abs(value):,.2f}"
    return f"-{amount}" if value < 0 else amount


def squash(text: str | None) -> str:
    """Lowercase and collapse whitespace so quotes can be compared with page text."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()
