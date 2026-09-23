"""Small helpers that turn messy printed values into comparable keys."""
import re
from datetime import date


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


def money(value: float | None) -> str:
    if value is None:
        return "n/a"
    return f"-${abs(value):,.2f}" if value < 0 else f"${value:,.2f}"


def squash(text: str | None) -> str:
    """Lowercase and collapse whitespace so quotes can be compared with page text."""
    return re.sub(r"\s+", " ", (text or "").lower()).strip()
