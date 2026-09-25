"""A person's decision on a held invoice is what the dashboard shows; tickd's own record stays for automation stats."""
from conftest import sample
from fastapi.testclient import TestClient

from app.main import app
from app.pipeline import run_invoice


def test_the_dashboard_counts_the_persons_decision():
    pdf, extraction = sample("T-05")
    result = run_invoice(pdf, extraction=extraction)
    assert result["decision"]["outcome"] == "Review"
    client = TestClient(app)
    before = client.get("/api/metrics").json()
    assert before["by_outcome"]["Review"] == 1 and before["open_reviews"] == 1

    client.post(f"/api/runs/{result['run_id']}/review", json={"action": "reject", "reason": "Bank change not confirmed"})

    after = client.get("/api/metrics").json()
    assert after["by_outcome"]["Review"] == 0 and after["by_outcome"]["Reject"] == 1
    assert after["open_reviews"] == 0 and after["resolved_by_people"] == 1
    assert after["straight_through"] == before["straight_through"]      # a person decided it, not tickd
    run = client.get(f"/api/runs/{result['run_id']}").json()
    assert run["status"] == "resolved" and run["decision"] == "Reject"
