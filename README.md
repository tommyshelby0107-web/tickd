# tickd by Sid — every invoice, ticked (PS-1)

**tickd** (said "ticked") takes a vendor invoice PDF and returns an explained decision: Approve, Review, Return to
vendor, or Reject. The name comes from the auditor's tick mark: the ✓ placed next to every figure that has been
checked against evidence.
Design: see the PS-1 Solution Design Pack.

## Setup

```powershell
python -m venv C:\Users\Acer\.venvs\invoice-agent   # kept outside OneDrive on purpose
C:\Users\Acer\.venvs\invoice-agent\Scripts\python.exe -m pip install -r requirements.txt
```

Install [Tesseract](https://github.com/UB-Mannheim/tesseract/wiki) for scanned PDFs, then copy `.env.example` to
`.env` and add the free API keys (Groq, Gemini, Mistral). Keys stay in `.env`, which git ignores.

## Who reads the invoice

| Step | Reader | Used when |
| --- | --- | --- |
| 1 | Python parser (no AI) | Digital PDFs and clean scans; accepted only if every line and total adds up |
| 2 | Qwen on Groq | The parser could not prove its reading (text only, fast) |
| 3 | Gemini | Qwen unavailable, or a page OCR could barely read (Gemini sees the image) |
| 4 | Mistral | Gemini busy; also sees images, from a different company |
| 5 | A human | Every reader busy or failed: never a guess |

Whoever reads it, only the rules decide.

## Three ways in, one queue

| Channel | How | Where |
| --- | --- | --- |
| Single invoice | Upload a PDF or pick a prepared scenario | New run |
| Folder | Choose a folder in the browser; every PDF in it is processed in filename order | Bulk run |
| Email | A dedicated Gmail inbox is polled every 20 s (IMAP + App Password); each PDF attachment is processed | Email inbox |

All three feed one work queue with one worker, so free-tier LLM limits are respected and duplicates inside a batch
are caught deterministically. Emailed invoices also get rule VM-04: the sender should be the vendor's own domain.

## Test data

`data/` holds the reference data the rules match against (vendor master, PO register with receipts and
quantities already invoiced, invoice history). `samples/invoices/` holds the generated PDFs and
`samples/manifest.json` the ground truth and expected decision for each one.

New vendors and purchase orders can be added in the app (Reference data → **Add vendor** / **Add PO**). They are
checked first: a vendor needs bank details and cannot duplicate an existing name, alias or tax ID; a PO must belong
to a known vendor, have a new number, and cannot record more received than ordered. Example: T-11 is held for
Procurement until its vendor (Northgate Industrial Solutions LLC) and PO-9981 are added, then the same PDF approves.
**Reset demo data** removes anything added.

Regenerate the PDFs:

```powershell
C:\Users\Acer\.venvs\invoice-agent\Scripts\python.exe scripts\generate_invoices.py
```

| Scenario | Vendor (layout) | Type | Expected decision | What it proves |
| --- | --- | --- | --- | --- |
| HP-1 | Apex Fasteners (classic) | digital | Approve | Clean path, exact PO match |
| HP-2 | Coastal Packaging (band) | digital | Approve with notes | Close-but-not-exact within tolerance, freight |
| EC-1A | Summit Electrical (compact) | digital | Reject | Already approved; duplicate detection |
| EC-1B | Summit Electrical (compact) | digital | Review (Buyer) | Split PO over-billed cumulatively (112.5%) |
| EC-2 | Apex Fasteners (classic) | scanned | Reject | HP-1 re-sent as a scan, number reformatted |
| EC-3 | Northline Safety (letter) | scanned | Review (AP) | No PO number; PO-4504 inferred |
| EC-4 | Brightpath Tools (grid) | digital | Review, high risk | Bank details changed on a perfect invoice |
| RV-1 | Coastal Packaging (band) | digital | Return to vendor | No invoice number or date |
| X-1 | Redline Industrial (classic) | scanned | Reject | Blocked vendor |
| X-2 | Apex Fasteners (classic) | digital | Review (Buyer) | Price 6% over PO |

Demo order matters for EC-2: run HP-1 first.

### Held-out test set (`samples/holdout/`)

Ten invoices from six new vendors in three new layouts, **never used to design or tune the rules**. They measure
how the system copes with invoices it has not seen. Regenerate with `scripts\generate_holdout.py`.

| Scenario | What it tests | Expected decision |
| --- | --- | --- |
| T-01 | Prices include sales tax | Approve (compared net of tax) |
| T-02 | Two-page invoice, 28 lines | Approve |
| T-03 | Lump-sum line instead of the PO's three lines | Review (Buyer) |
| T-04 | Invoice against a closed, fully billed PO | Review (Buyer) |
| T-05 | Billed for 300 pallets, 180 received | Review (Warehouse) |
| T-06 | Line typed 609.00 instead of 690.00 | Review (AP), arithmetic |
| T-07 | Same vendor and amount as a paid invoice 13 days earlier, new number | Review (AP), possible duplicate |
| T-08 | Vendor not in the vendor master (scanned) | Review (Procurement) |
| T-09 | Fax-grade scan of a clean invoice | Approve, or a low-confidence Review |
| T-10 | Credit note | Review (AP): never paid as a bill |
| T-11 | No master data at all: unknown vendor, PO-9981 not in the register, unknown items | Review (Procurement); Approve disabled |

```powershell
& $py scripts\evaluate.py holdout truth    # rules only, perfect extraction, no API calls
& $py scripts\evaluate.py holdout live     # OCR + LLM + rules, the real test
& $py scripts\evaluate.py demo cached      # regression check on saved extractions
```
