"""Tests for freshness filtering, keyword matching and de-duplication."""
from datetime import datetime, timedelta, timezone

from app.services.aggregator import collect
from app.sources import RawJob, SearchQuery
from app.sources.base import JobSource


def _job(**kw) -> RawJob:
    defaults = dict(
        source="test",
        external_id="1",
        title="Python Engineer",
        company="Acme",
        description="We use Python and FastAPI",
        posted_at=datetime.now(timezone.utc),
    )
    defaults.update(kw)
    return RawJob(**defaults)


class FakeSource(JobSource):
    name = "fake"

    def __init__(self, jobs):
        self._jobs = jobs

    def fetch(self, query):
        return self._jobs


def _collect_with(jobs, query, monkeypatch):
    import app.services.aggregator as agg

    monkeypatch.setattr(agg, "get_sources", lambda names=None: [FakeSource(jobs)])
    return collect(query)


def test_filters_out_stale_jobs(monkeypatch):
    stale = _job(external_id="old", posted_at=datetime.now(timezone.utc) - timedelta(hours=48))
    fresh = _job(external_id="new", posted_at=datetime.now(timezone.utc) - timedelta(hours=2))
    result = _collect_with([stale, fresh], SearchQuery(max_age_hours=24), monkeypatch)
    ids = {j.external_id for j in result}
    assert ids == {"new"}


def test_excludes_jobs_with_unknown_age(monkeypatch):
    unknown = _job(external_id="u", posted_at=None)
    result = _collect_with([unknown], SearchQuery(max_age_hours=24), monkeypatch)
    assert result == []


def test_keyword_matching(monkeypatch):
    match = _job(external_id="m", title="Senior Python Dev")
    nomatch = _job(external_id="n", title="Sales Manager", description="quota driven")
    result = _collect_with(
        [match, nomatch], SearchQuery(keywords=["python"], max_age_hours=24), monkeypatch
    )
    assert {j.external_id for j in result} == {"m"}


def test_dedupe_keeps_newest(monkeypatch):
    older = _job(external_id="a", posted_at=datetime.now(timezone.utc) - timedelta(hours=5))
    newer = _job(external_id="b", posted_at=datetime.now(timezone.utc) - timedelta(hours=1))
    result = _collect_with([older, newer], SearchQuery(max_age_hours=24), monkeypatch)
    assert len(result) == 1
    assert result[0].external_id == "b"


def test_remote_only_filter(monkeypatch):
    onsite = _job(external_id="o", location="New York, NY", tags=[])
    remote = _job(external_id="r", location="Remote", tags=["remote"])
    result = _collect_with(
        [onsite, remote], SearchQuery(remote_only=True, max_age_hours=24), monkeypatch
    )
    assert {j.external_id for j in result} == {"r"}
