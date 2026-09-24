"""A folder of invoices goes through the one work queue, in filename order, through the real API."""
import time

from conftest import MANIFEST
from fastapi.testclient import TestClient

from app import config
from app.main import app


def wait_for(client: TestClient, batch_id: str, timeout: float = 90) -> dict:
    deadline = time.time() + timeout
    while time.time() < deadline:
        batch = client.get(f"/api/batches/{batch_id}").json()
        if all(r["status"] == "done" for r in batch["runs"]):
            return batch
        time.sleep(0.3)
    raise AssertionError("batch did not finish in time")


def test_folder_batch_processes_every_pdf_and_catches_the_duplicate_inside_it(monkeypatch):
    monkeypatch.setattr(config, "EXTRACTION_MODE", "cached")          # saved LLM readings: no API calls in tests
    upload = [("files", (MANIFEST[s]["file"], MANIFEST[s]["path"].read_bytes(), "application/pdf"))
              for s in ("HP-1", "EC-2", "X-1")]
    upload.append(("files", ("notes.txt", b"not an invoice", "text/plain")))
    with TestClient(app) as client:
        started = client.post("/api/batches", files=upload, data={"name": "Morning inbox"}).json()
        assert started["queued"] == 3 and started["skipped"] == ["notes.txt (not a PDF)"]
        batch = wait_for(client, started["batch_id"])

    by_file = {r["file_name"][:4]: r for r in batch["runs"]}
    # EC-2 sorts first, so it is the copy that gets paid; HP-1 (same invoice) is then caught as its duplicate
    assert [r["file_name"][:4] for r in batch["runs"]] == ["EC-2", "HP-1", "X-1_"]
    assert by_file["EC-2"]["decision"] == "Approve"
    assert by_file["HP-1"]["decision"] == "Reject" and "Duplicate" in by_file["HP-1"]["summary"]
    assert by_file["X-1_"]["decision"] == "Reject" and "Blocked" in by_file["X-1_"]["summary"]
    assert all(r["source"] == "folder" and r["source_detail"] == "Morning inbox" for r in batch["runs"])


def test_batch_with_no_pdfs_is_refused():
    with TestClient(app) as client:
        response = client.post("/api/batches", files=[("files", ("readme.md", b"# hi", "text/markdown"))])
    assert response.status_code == 400
