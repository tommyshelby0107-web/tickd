"""Email intake: poll a dedicated inbox over IMAP and queue every PDF attachment as an invoice run.

Invoices arriving by email then go through exactly the same queue, pipeline and rules as uploads and folders.
"""
import email
import imaplib
import logging
import threading
import time
from dataclasses import dataclass, field
from email import policy
from email.utils import parseaddr, parsedate_to_datetime
from pathlib import Path
from typing import Callable

from . import config, db
from .pipeline import new_run_id

MAX_PDF_BYTES = 10 * 1024 * 1024
_poll_lock = threading.Lock()          # the background poller and the "Check now" button never poll at once
STATUS: dict = {"last_checked": None, "last_error": None, "last_new": 0}


@dataclass
class ParsedEmail:
    message_id: str
    sender: str
    sender_name: str
    subject: str
    received_at: str | None
    attachments: list[tuple[str, bytes]] = field(default_factory=list)   # (filename, PDF bytes)
    ignored: list[str] = field(default_factory=list)                     # other attachments, with the reason


def parse_message(raw: bytes) -> ParsedEmail:
    """Pull sender, subject and every PDF attachment out of a raw email, including PDFs inside forwarded emails."""
    msg = email.message_from_bytes(raw, policy=policy.default)
    name, address = parseaddr(str(msg.get("From", "")))
    try:
        received = parsedate_to_datetime(str(msg["Date"])).isoformat()
    except (TypeError, ValueError):
        received = None
    parsed = ParsedEmail(message_id=str(msg.get("Message-ID", "")).strip(), sender=address.lower(),
                         sender_name=name, subject=str(msg.get("Subject", "")), received_at=received)
    for part in msg.walk():             # walk() also descends into forwarded (message/rfc822) emails
        filename = part.get_filename()
        if part.is_multipart() or not filename:
            continue
        data = part.get_payload(decode=True) or b""
        if not (part.get_content_type() == "application/pdf" or filename.lower().endswith(".pdf")):
            parsed.ignored.append(f"{filename} (not a PDF)")
        elif not data.startswith(b"%PDF"):
            parsed.ignored.append(f"{filename} (not a readable PDF)")
        elif len(data) > MAX_PDF_BYTES:
            parsed.ignored.append(f"{filename} (larger than 10 MB)")
        else:
            parsed.attachments.append((Path(filename).name, data))
    return parsed


Enqueue = Callable[..., str]


def queue_email(parsed: ParsedEmail, enqueue: Enqueue) -> list[str]:
    """Save each PDF attachment and put it on the work queue; log the email either way."""
    run_ids = []
    detail = f"{parsed.sender_name or parsed.sender} · {parsed.subject}"[:200]
    for filename, data in parsed.attachments:
        run_id = new_run_id()
        path = config.uploads_dir() / run_id / filename
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(data)
        run_ids.append(enqueue(path, "email", source_detail=detail, email_from=parsed.sender, run_id=run_id))
    db.log_email(parsed.message_id, parsed.sender, parsed.sender_name, parsed.subject, parsed.received_at,
                 run_ids, parsed.ignored if parsed.attachments else parsed.ignored + ["no PDF attachment"])
    return run_ids


def poll_once(enqueue: Enqueue, connect: Callable[[], imaplib.IMAP4] | None = None) -> dict:
    """Fetch unread emails, queue their PDFs, mark them read. Returns a small summary for the UI."""
    connect = connect or (lambda: imaplib.IMAP4_SSL(config.EMAIL_IMAP_HOST))
    with _poll_lock:
        try:
            client = connect()
            try:
                client.login(config.EMAIL_ADDRESS, config.EMAIL_APP_PASSWORD)
                client.select(config.EMAIL_FOLDER)
                _, data = client.uid("search", None, "UNSEEN")
                new = 0
                for uid in (data[0].split() if data and data[0] else []):
                    _, parts = client.uid("fetch", uid, "(BODY.PEEK[])")      # PEEK: only mark read once queued
                    raw = next(p[1] for p in parts if isinstance(p, tuple))
                    parsed = parse_message(raw)
                    if not db.email_seen(parsed.message_id):                 # never process the same email twice
                        queue_email(parsed, enqueue)
                        new += 1
                    client.uid("store", uid, "+FLAGS", "(\\Seen)")
            finally:
                try:
                    client.logout()
                except Exception:
                    pass
        except Exception as exc:
            STATUS.update(last_checked=db.now(), last_error=f"{type(exc).__name__}: {exc}")
            raise
        STATUS.update(last_checked=db.now(), last_error=None, last_new=new)
        return dict(STATUS)


def start_poller(enqueue: Enqueue) -> None:
    def loop() -> None:
        while True:
            try:
                poll_once(enqueue)
            except Exception:
                logging.exception("email poll failed")       # recorded in STATUS; keep polling
            time.sleep(config.EMAIL_POLL_SECONDS)

    threading.Thread(target=loop, daemon=True, name="email-poller").start()
