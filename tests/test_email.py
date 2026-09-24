"""Email intake (with a fake IMAP server, so no real inbox is needed) and the VM-04 sender check."""
import time
from email.message import EmailMessage

import pytest
from conftest import MANIFEST, sample
from fastapi.testclient import TestClient

from app import config, db, email_intake
from app.pipeline import run_invoice

HP1 = MANIFEST["HP-1"]["path"].read_bytes()
X1 = MANIFEST["X-1"]["path"].read_bytes()


def make_email(sender: str, msg_id: str, pdfs=(("invoice.pdf", HP1),), forwarded_pdf: bytes | None = None) -> bytes:
    m = EmailMessage()
    m["From"], m["To"], m["Subject"] = sender, "ap@meridian.example", "Invoice attached"
    m["Message-ID"], m["Date"] = msg_id, "Thu, 24 Sep 2026 10:00:00 +0000"
    m.set_content("Please find our invoice attached.")
    for name, data in pdfs:
        m.add_attachment(data, maintype="application", subtype="pdf", filename=name)
    m.add_attachment(b"\x89PNG fake logo", maintype="image", subtype="png", filename="logo.png")
    if forwarded_pdf:
        inner = EmailMessage()
        inner["From"], inner["Subject"] = "billing@redlineindustrial.example", "Original invoice"
        inner.set_content("see attached")
        inner.add_attachment(forwarded_pdf, maintype="application", subtype="pdf", filename="forwarded.pdf")
        m.add_attachment(inner)                       # attached as message/rfc822, like a forward
    return m.as_bytes()


class FakeImap:
    """Just enough of imaplib's interface: every message stays 'unseen' unless flagged."""
    def __init__(self, messages: dict[bytes, bytes]):
        self.messages, self.seen = messages, set()

    def login(self, user, password): return "OK", [b"logged in"]
    def select(self, folder): return "OK", [b"1"]
    def logout(self): return "BYE", []

    def uid(self, command, *args):
        if command == "search":
            return "OK", [b" ".join(u for u in self.messages if u not in self.seen)]
        if command == "fetch":
            return "OK", [(b"1 (BODY[] {1}", self.messages[args[0]]), b")"]
        if command == "store":
            self.seen.add(args[0])
            return "OK", []


def test_parse_takes_pdfs_including_forwarded_ones_and_ignores_the_rest():
    parsed = email_intake.parse_message(make_email("Apex AR <ar@apexfasteners.example>", "<a@x>", forwarded_pdf=X1))
    assert parsed.sender == "ar@apexfasteners.example" and parsed.sender_name == "Apex AR"
    assert [name for name, _ in parsed.attachments] == ["invoice.pdf", "forwarded.pdf"]
    assert parsed.ignored == ["logo.png (not a PDF)"]


def test_poll_queues_each_pdf_once_marks_read_and_logs_the_email(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_ADDRESS", "ap.demo@example.com")
    monkeypatch.setattr(config, "EMAIL_APP_PASSWORD", "x")
    queued = []

    def fake_enqueue(path, source, source_detail=None, email_from=None, run_id=None):
        queued.append((path.name, source, email_from))
        return run_id

    server = FakeImap({b"1": make_email("ar@apexfasteners.example", "<m1@x>"),
                       b"2": make_email("someone@example.org", "<m2@x>", pdfs=())})
    email_intake.poll_once(fake_enqueue, connect=lambda: server)
    assert queued == [("invoice.pdf", "email", "ar@apexfasteners.example")]
    assert server.seen == {b"1", b"2"}
    log = db.email_log()
    assert len(log) == 2 and "no PDF attachment" in log[0]["ignored"]

    server.seen.clear()                                     # even if the mailbox shows them unread again...
    email_intake.poll_once(fake_enqueue, connect=lambda: server)
    assert len(queued) == 1                                 # ...the same email is never processed twice


def test_emailed_invoice_goes_through_the_queue_end_to_end(monkeypatch):
    monkeypatch.setattr(config, "EXTRACTION_MODE", "cached")
    # email stays "not configured" here, so the app never starts a real poller; the fake server is used directly
    from app.main import app, enqueue
    with TestClient(app):
        email_intake.poll_once(enqueue, connect=lambda: FakeImap({b"7": make_email("ar@apexfasteners.example", "<e2e@x>")}))
        run_id = db.email_log()[0]["runs"][0]["run_id"]
        deadline = time.time() + 60
        while db.run(run_id)["status"] != "done" and time.time() < deadline:
            time.sleep(0.2)
    run = db.run(run_id)
    assert run["source"] == "email" and run["decision"] == "Approve"
    vm04 = next(f for f in run["result"]["findings"] if f["rule"] == "VM-04")
    assert vm04["outcome"] == "pass"


def run_from(sender: str) -> dict:
    pdf, extraction = sample("HP-1")
    db.create_run("r1", pdf.name, "hash", status="queued", source="email", email_from=sender)
    return run_invoice(pdf, run_id="r1", extraction=extraction)


@pytest.mark.parametrize("sender, outcome, severity, decision", [
    ("ar@apexfasteners.example", "pass", "normal", "Approve"),             # the vendor's own domain
    ("invoices@notification.intuit.com", "pass", "normal", "Approve"),     # a known invoicing platform
    ("billing@apex-fasteners-billing.com", "review", "high", "Review"),    # lookalike domain: impersonation
    ("randomperson@gmail.com", "review", "normal", "Review"),              # unrelated address
])
def test_sender_check(sender, outcome, severity, decision):
    result = run_from(sender)
    vm04 = next(f for f in result["findings"] if f["rule"] == "VM-04")
    assert (vm04["outcome"], vm04["severity"], result["decision"]["outcome"]) == (outcome, severity, decision)


def test_trusted_forwarder_is_a_note_not_a_hold(monkeypatch):
    monkeypatch.setattr(config, "EMAIL_TRUSTED_FORWARDERS", ["me@gmail.com"])
    result = run_from("me@gmail.com")
    assert result["decision"]["outcome"] == "Approve"
    assert next(f for f in result["findings"] if f["rule"] == "VM-04")["outcome"] == "note"
