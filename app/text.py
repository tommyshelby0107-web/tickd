"""Get the text of every page: from the PDF's text layer if it has one, otherwise by OCR."""
from dataclasses import dataclass, field
from pathlib import Path

import pdfplumber
import pymupdf
import pytesseract
from PIL import Image

from .config import TESSERACT_CMD

pytesseract.pytesseract.tesseract_cmd = TESSERACT_CMD

MIN_TEXT_CHARS = 30      # a page with less real text than this is treated as a scan
OCR_DPI = 300
TESSERACT_CONFIG = "--psm 6"   # read the page as one block, row by row, so table rows stay together


@dataclass
class PageText:
    number: int
    text: str
    source: str                                   # "text-layer" or "ocr"
    ocr_confidence: float | None = None           # mean word confidence 0-100 (OCR pages only)
    words: list[tuple[str, float]] = field(default_factory=list)   # (word, confidence) for OCR pages


def read_pages(pdf_path: Path) -> list[PageText]:
    with pdfplumber.open(pdf_path) as pdf:
        layers = [page.extract_text() or "" for page in pdf.pages]
    pages = []
    with pymupdf.open(pdf_path) as doc:
        for i, text in enumerate(layers):
            if len(text.strip()) >= MIN_TEXT_CHARS:
                pages.append(PageText(i + 1, text, "text-layer"))
            else:
                pages.append(ocr_page(doc[i], i + 1))
    return pages


def ocr_page(page: pymupdf.Page, number: int) -> PageText:
    pix = page.get_pixmap(dpi=OCR_DPI, colorspace=pymupdf.csGRAY)
    image = Image.frombytes("L", (pix.width, pix.height), pix.samples)
    data = pytesseract.image_to_data(image, config=TESSERACT_CONFIG, output_type=pytesseract.Output.DICT)
    lines: dict[tuple[int, int, int], list[str]] = {}
    words: list[tuple[str, float]] = []
    for i, word in enumerate(data["text"]):
        confidence = float(data["conf"][i])
        if not word.strip() or confidence < 0:
            continue
        key = (data["block_num"][i], data["par_num"][i], data["line_num"][i])
        lines.setdefault(key, []).append(word)
        words.append((word, confidence))
    text = "\n".join(" ".join(line) for line in lines.values())
    mean = round(sum(c for _, c in words) / len(words), 1) if words else 0.0
    return PageText(number, text, "ocr", mean, words)


def page_png(pdf_path: Path, number: int, dpi: int = 150) -> bytes:
    """Render one page as PNG, for the UI preview and the LLM image fallback."""
    with pymupdf.open(pdf_path) as doc:
        return doc[number - 1].get_pixmap(dpi=dpi).tobytes("png")


def as_prompt_text(pages: list[PageText]) -> str:
    return "\n\n".join(f"=== Page {p.number} ({p.source}) ===\n{p.text}" for p in pages)
