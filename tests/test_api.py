"""End-to-end API tests using an isolated sqlite DB and no real network."""
import os
import tempfile

import pytest


@pytest.fixture()
def client(monkeypatch):
    # Use a throwaway DB and dry-run email before app import.
    tmpdir = tempfile.mkdtemp()
    db_path = os.path.join(tmpdir, "test.db")
    monkeypatch.setenv("DATABASE_URL", f"sqlite:///{db_path}")
    monkeypatch.setenv("EMAIL_DRY_RUN", "true")
    monkeypatch.setenv("GENERATOR_BACKEND", "template")

    # Reset cached settings so env vars take effect.
    from app.config import get_settings

    get_settings.cache_clear()

    # Import modules fresh so the engine binds to the temp DB.
    import importlib

    import app.database as database

    importlib.reload(database)
    # Reload models AFTER database so their tables register on the new Base.metadata.
    import app.models as models

    importlib.reload(models)
    import app.services.aggregator as aggregator

    importlib.reload(aggregator)
    import app.main as main

    importlib.reload(main)

    from fastapi.testclient import TestClient

    with TestClient(main.app) as c:
        yield c


def test_health(client):
    r = client.get("/api/health")
    assert r.status_code == 200
    assert r.json()["email_dry_run"] is True


def test_profile_roundtrip(client):
    r = client.put("/api/profile", json={"full_name": "Jane Doe", "skills": "Python, FastAPI"})
    assert r.status_code == 200
    assert r.json()["full_name"] == "Jane Doe"
    assert client.get("/api/profile").json()["skills"] == "Python, FastAPI"


def _seed_job(client):
    """Insert a job directly via the DB session for a deterministic test."""
    from datetime import datetime, timezone

    import app.main as main
    from app.models import Job

    session = main.SessionLocal() if hasattr(main, "SessionLocal") else None
    from app.database import SessionLocal

    s = SessionLocal()
    job = Job(
        source="test",
        external_id="x1",
        title="Python Engineer",
        company="Acme",
        description="Python and FastAPI",
        apply_email="jobs@acme.example",
        posted_at=datetime.now(timezone.utc).replace(tzinfo=None),
    )
    s.add(job)
    s.commit()
    jid = job.id
    s.close()
    return jid


def test_generate_review_and_send_flow(client):
    client.put("/api/profile", json={"full_name": "Jane Doe", "skills": "Python, FastAPI"})
    job_id = _seed_job(client)

    # jobs list shows the fresh job
    jobs = client.get("/api/jobs").json()
    assert any(j["id"] == job_id for j in jobs)

    # generate documents
    r = client.post(f"/api/jobs/{job_id}/generate", json={})
    assert r.status_code == 200
    app_id = r.json()["id"]
    assert r.json()["status"] == "generated"
    assert "Jane Doe" in r.json()["resume"]

    # cannot send before approval
    r = client.post(f"/api/applications/{app_id}/send", json={})
    assert r.status_code == 409

    # approve then send (dry-run writes to outbox)
    client.put(f"/api/applications/{app_id}", json={"status": "approved"})
    r = client.post(f"/api/applications/{app_id}/send", json={})
    assert r.status_code == 200, r.text
    assert r.json()["status"] == "sent"
    assert r.json()["sent_to"] == "jobs@acme.example"
