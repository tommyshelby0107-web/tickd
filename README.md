# Invoice Agent — PS-1

Takes a vendor invoice PDF and returns an explained decision: Approve, Review, Return to vendor, or Reject.
Design: see the PS-1 Solution Design Pack.

## Setup

```powershell
python -m venv C:\Users\Acer\.venvs\invoice-agent   # kept outside OneDrive on purpose
C:\Users\Acer\.venvs\invoice-agent\Scripts\python.exe -m pip install -r requirements.txt
```

## Test data

`data/` holds the reference data the rules match against (vendor master, PO register with receipts and
quantities already invoiced, invoice history). `samples/invoices/` holds the generated PDFs and
`samples/manifest.json` the ground truth and expected decision for each one.

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
