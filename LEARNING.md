# Study guide — how the invoice agent works

Read this top to bottom once, then do the exercises at the end. Goal: you can explain every file and every
decision without notes.

## 1. The one-sentence pitch

"An invoice PDF goes in; the AI only *reads* it; plain rules *decide*; every decision comes out with its
reason, its evidence and a drafted next step — and anything doubtful goes to a human."

## 2. The flow (8 stages)

```
PDF ─► 1 Intake ─► 2 Extract ─► 3 Validate ─► 4 Vendor ─► 5 Duplicates ─► 6 PO match ─► 7 Line match ─► 8 Decide
       text / OCR   Gemini→JSON  maths, dates   master,      3 layers        printed or     price, qty,       Approve / Review /
                                 evidence       bank, tax                    inferred       cumulative        Return / Reject
```

Every check produces a **Finding**: `rule`, `outcome` (pass / note / review / return / reject), `message`,
`owner`. Stage 8 picks the most severe outcome. That is the whole engine.

## 3. File by file

| File | What it does | The idea to remember |
| --- | --- | --- |
| `app/text.py` | Gets page text. pdfplumber for digital PDFs; Tesseract OCR for scans (with a confidence per word) | Use the cheapest tool that works: no OCR when the PDF already has text |
| `app/extract.py` | Sends page text to Gemini with a **schema** (Pydantic). Gets back typed fields, each critical one with a `source_quote` | Structured output = no fragile JSON parsing. The quote lets code check the AI didn't invent a value |
| `app/rules.py` | All checks, stages 3–7. Pure Python, no AI | Deterministic: same invoice → same decision → auditable |
| `app/decide.py` | Picks the outcome, lead reason, explanation, next action, draft email | Severity order: Reject > Return > Review (high) > Review > Approve |
| `app/pipeline.py` | Runs stages in order, records an event per stage, never crashes into an Approve | Any error ends in human review |
| `app/db.py` | SQLite: vendors, POs, invoice registry, runs, events, ledger | Approval *consumes* PO quantities — that is how split invoices are caught |
| `app/normalize.py` | Makes `INV 2026 0457` and `INV-2026-0457` the same key | Duplicate detection is only as good as normalisation |
| `policy.yaml` | Tolerances and thresholds | Business owns the numbers; changing them needs no code |

## 4. Why each design choice (your interview answers)

- **Why not let the LLM decide?** LLMs are not deterministic or auditable. Finance needs "same input, same
  output" and a rule an auditor can read. So the LLM reads; rules decide.
- **How do you know the LLM didn't hallucinate a number?** Three ways: (1) it must quote where it found each
  critical value and code checks the quote is on the page; (2) arithmetic must reconcile (lines → subtotal →
  total); (3) OCR'd words need ≥80 confidence. Fail any → human review.
- **Why is a perfect match not enough (EC-4)?** Bank-detail change fraud (business email compromise) sends a
  genuine-looking invoice with new bank details. Every commercial check passes. Only comparing the remit-to
  account with the vendor master catches it — and it is routed as high risk with "call the number on file".
- **Why not auto-approve an inferred PO (EC-3)?** Wrong approval costs money; a review costs minutes. The
  system does the work (finds PO-4504, score 0.92 vs 0.21) and a human confirms in one click.
- **How are split invoices caught (EC-1)?** Each PO line tracks `qty_invoiced`. Approval adds to it. The next
  invoice is judged against what is left, not against the whole PO.
- **Why Tesseract + Gemini, not just one?** Tesseract is free and gives confidence scores (evidence), but only
  produces raw text. The LLM turns text from *any* layout into fields. Regex templates would break on every
  new vendor format.
- **Why templates, not an LLM, for explanations?** One fewer API call per invoice, and the explanation can
  never say something the rules did not find.
- **What would you do for a real client?** Paid LLM tier (free tiers may train on data), ERP API instead of
  CSVs, email inbox intake, approval matrix for non-PO invoices, weekly review of human overrides to tune
  thresholds.

## 5. Finance words you must be fluent in

| Term | Meaning |
| --- | --- |
| PO (purchase order) | What the company agreed to buy: items, quantities, prices |
| GRN / goods receipt | Record that the goods actually arrived |
| 2-way match | Invoice vs PO |
| 3-way match | Invoice vs PO vs goods receipt (we do this: `qty_received`) |
| Tolerance | Allowed gap before a human must look (ours: 2% and max $250) |
| STP (straight-through processing) | Invoices decided with no human touch |
| Vendor master | The approved list of vendors, with bank details |
| BEC (business email compromise) | Fraud where criminals change the bank details on a real-looking invoice |
| Accrual | Recording a cost before it's paid; why month-end needs invoices processed fast |

## 6. Commands

```powershell
$py = "C:\Users\Acer\.venvs\invoice-agent\Scripts\python.exe"
& $py -m pytest -q                      # all scenario tests (no API calls)
& $py scripts\demo_offline.py           # every scenario's decision and explanation, no API
& $py scripts\check_extraction.py       # real Gemini extraction scored against ground truth (needs key)
& $py scripts\generate_invoices.py      # rebuild the sample PDFs
```

## 7. Days 2–4: what was added and why

| Topic | What we did | Why (say this in the interview) |
| --- | --- | --- |
| Two LLM providers | Groq first (fast), Gemini as backup (also reads page images) | Free tiers get overloaded. We measured 13–113 s per invoice on free Gemini alone. Graceful degradation beats a stuck demo |
| Model fallback chain | Each provider tries a list of models; a busy one (429/503) is skipped immediately | Waiting on an overloaded model wastes the user's time; the run records which model answered, so it's transparent |
| Strict JSON schema | The same Pydantic model becomes Groq's strict schema (constrained decoding) and Gemini's response schema | The model *cannot* return malformed or extra fields, so there is no fragile JSON parsing |
| Deterministic clean-up | If the model quotes "Your PO PO-4507" but leaves the PO field empty, code fills it from the quote | Code double-checks the AI. We found this with the accuracy checker (89/90 → 90/90) |
| Accuracy checker | `check_extraction.py` scores each field against the answer key | You can't improve what you don't measure. It's your answer to "how accurate is it?" |
| Live view (SSE) | Each stage writes an event to SQLite; the browser streams them with Server-Sent Events | Stored first, so a page reload replays the run. SSE is one-way server→browser, simpler than WebSockets, which we don't need |
| Stage pause (0.4 s) | Small pause between rule stages, 0 in tests | Rules finish in milliseconds; people watching need to see each stage. It's a display setting, not fake work |
| Cached mode | Known sample PDFs can reuse their saved extraction; the UI says "cached extraction (no LLM call)" | For UI work without burning quota, and an honest backup if the internet fails in the demo |
| Escaping | Every value from a PDF is HTML-escaped before display | An invoice is untrusted input. A malicious PDF could otherwise inject script into the reviewer's browser |
| UTC timestamps | Server stores UTC with offset; browser shows local time | A hosted server (UTC) and a viewer in India would otherwise disagree by 5.5 hours |

## 8. The held-out test set (your strongest interview story)

**The idea:** the 10 demo invoices were used while *designing* the rules, so passing them proves little — like a
student marking their own homework. So we built 10 more invoices from 6 new vendors in 3 new layouts and never
looked at them while designing. Then we ran them **blind**, before changing any code.

**What the blind run found (rules only, perfect data): 7 of 10.** Three real gaps:

| Gap | Symptom | Fix |
| --- | --- | --- |
| Tax-included prices (T-01) | Held for a fake "+7.5% price variance" | When the invoice says tax is included, compare prices net of that tax |
| Lead reason (T-06) | Arithmetic error routed to the Buyer as a "price variance" | If the invoice's own maths is wrong, that leads and goes to AP — nothing else on it can be trusted |
| Credit notes (T-10) | Held only by luck; no concept of a credit note | New rule V-06. The LLM classifies the document **and** code checks two deterministic signals: a negative total or the words "credit note/memo" on the page |

After the fixes: 10/10 held-out, 10/10 demo still passing, 39 tests.

**How to say it:** "I split my test data into a design set and a held-out set. The held-out set caught three
gaps a real AP team would hit — tax-inclusive vendors, arithmetic errors and credit notes. I fixed them and added
regression tests so they can't come back. In production I'd keep doing this with real invoices: every human
override becomes a new test case."

## 9. Bulk and email intake

- **One queue, one worker.** Uploads, folders and email all create a "queued" run and put it on the same queue.
  One worker processes them in order. Why one? Free-tier LLM rate limits, and determinism: if a folder holds the
  same invoice twice, the first (by filename) is the original and the second is caught by D-02.
- **Folder picker in the browser**, not a folder the server watches: a watched folder only works on your laptop;
  the browser picker also works when the app is hosted.
- **Email = IMAP polling.** Every 20 s the app logs in to a dedicated Gmail (App Password), fetches unread emails,
  saves each PDF attachment (also inside forwarded emails), queues it, and marks the email read. Every email is
  logged by Message-ID, so even if it shows up unread again it is never processed twice.
- **VM-04 sender check.** Vendor's own domain or a known invoicing platform: pass. A trusted internal forwarder:
  note. A lookalike domain (apex-fasteners-billing.com vs apexfasteners.example): high-risk hold. Anything else:
  review. Business email compromise often starts with exactly this.
- **Alternatives you should be able to name:** inbound webhooks (Postmark/SendGrid: instant, needs a public URL),
  Power Automate for Microsoft 365 ("When a new email arrives" → HTTP POST to our API), Gmail API / Graph with
  OAuth (production-grade). Outlook no longer allows simple password IMAP, which is why Gmail was the quick path.

## 10. Running the app

```powershell
cd "C:\Users\Acer\OneDrive\Desktop\zamp ai\invoice-agent"
& "C:\Users\Acer\.venvs\invoice-agent\Scripts\python.exe" -m uvicorn app.main:app --port 8000
# open http://127.0.0.1:8000
# add  $env:EXTRACTION_MODE = "cached"  before the command to use saved extractions (no API calls)
```

## 11. Exercises (do these — this is how you learn the code)

1. In `policy.yaml`, change `header_tolerance_abs` from `250.00` to `50.00`. Run `demo_offline.py`.
   HP-2 should flip from Approve to Review. Why? (Its +$96 variance now exceeds $50.) Change it back.
2. In `data/vendors.csv`, set Brightpath's `bank_account` to `773001925561`. Run `demo_offline.py`. EC-4
   should now approve. What does that tell you about where the fraud check gets its truth? Change it back.
3. Open `app/rules.py`, find `M-03`. Explain in your own words, with EC-1B's numbers, why it fires.
4. In `app/normalize.py`, what does `invoice_key("INV-0098")` return? Predict first, then check in Python.
5. Explain to an imaginary CFO, in 30 seconds and with no technical words, what happens to EC-4.
6. In the app: Reference data → Reset. Run HP-1, then EC-2. Open Reference data: why is PO-4501 now 100% billed,
   and why did EC-2 get rejected even though its file and number format differ?
7. Run EC-3. Resolve it with Approve and the reason "Confirmed PO-4504 with buyer Dana Whitfield".
   Check Reference data: what changed for PO-4504, and what appeared in the invoice registry?
8. Open `app/extract.py` and find `_groq`. Walk through what happens, line by line, if Groq returns 503.
9. Open `tests/test_holdout.py`, test `test_credit_note_is_never_approved_even_if_read_as_positive`. Explain why
   we don't trust the LLM's `document_type` alone, and which two signals back it up.
