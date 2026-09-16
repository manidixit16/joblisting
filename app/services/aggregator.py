"""Aggregate listings from all sources: freshness filter, keyword match, dedup."""
from __future__ import annotations

import re
from datetime import datetime, timedelta, timezone

from sqlalchemy import select
from sqlalchemy.orm import Session

from ..models import Job
from ..sources import RawJob, SearchQuery, get_sources


def _normalize(text: str) -> str:
    return re.sub(r"\s+", " ", (text or "").strip().lower())


def _dedupe_key(job: RawJob) -> str:
    return f"{_normalize(job.title)}::{_normalize(job.company)}"


def _matches_keywords(job: RawJob, keywords: list[str]) -> bool:
    if not keywords:
        return True
    haystack = " ".join(
        [job.title, job.company, job.description, " ".join(job.tags)]
    ).lower()
    return any(kw.strip().lower() in haystack for kw in keywords if kw.strip())


def _is_fresh(job: RawJob, max_age_hours: int) -> bool:
    if job.posted_at is None:
        return False  # unknown age -> exclude to honor the freshness requirement
    posted = job.posted_at
    if posted.tzinfo is None:
        posted = posted.replace(tzinfo=timezone.utc)
    cutoff = datetime.now(timezone.utc) - timedelta(hours=max_age_hours)
    return posted >= cutoff


def collect(query: SearchQuery, source_names: list[str] | None = None) -> list[RawJob]:
    """Fetch from sources and apply freshness + keyword filters and de-dup.

    Returns a fresh, keyword-matched, de-duplicated list sorted newest-first.
    Never raises on individual source failure.
    """
    seen: dict[str, RawJob] = {}
    for source in get_sources(source_names):
        try:
            raw = source.fetch(query)
        except Exception:
            raw = []
        for job in raw:
            if not _is_fresh(job, query.max_age_hours):
                continue
            if query.remote_only and "remote" not in (
                job.location + " " + " ".join(job.tags)
            ).lower():
                continue
            if not _matches_keywords(job, query.keywords):
                continue
            key = _dedupe_key(job)
            # Keep the newest of any duplicates.
            existing = seen.get(key)
            if existing is None or (
                job.posted_at and existing.posted_at and job.posted_at > existing.posted_at
            ):
                seen[key] = job

    results = list(seen.values())
    results.sort(key=lambda j: j.posted_at or datetime.min.replace(tzinfo=timezone.utc), reverse=True)
    return results


def upsert_jobs(session: Session, jobs: list[RawJob]) -> tuple[int, int]:
    """Insert new jobs, update applicant counts on existing ones.

    Returns (new_count, updated_count).
    """
    new_count = 0
    updated_count = 0
    for raw in jobs:
        existing = session.scalar(
            select(Job).where(Job.source == raw.source, Job.external_id == raw.external_id)
        )
        if existing:
            if raw.applicants is not None and raw.applicants != existing.applicants:
                existing.applicants = raw.applicants
                updated_count += 1
            continue
        session.add(
            Job(
                source=raw.source,
                external_id=raw.external_id,
                title=raw.title,
                company=raw.company,
                location=raw.location,
                url=raw.url,
                description=raw.description,
                salary=raw.salary,
                tags=",".join(raw.tags),
                apply_email=raw.apply_email,
                applicants=raw.applicants,
                posted_at=(raw.posted_at or datetime.now(timezone.utc)).replace(tzinfo=None),
            )
        )
        new_count += 1
    session.commit()
    return new_count, updated_count
