"""Remotive source. Public JSON API: https://remotive.com/api/remote-jobs

Supports a `search` param. No applicant counts are exposed.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import JobSource, RawJob, SearchQuery

API_URL = "https://remotive.com/api/remote-jobs"


class RemotiveSource(JobSource):
    name = "remotive"

    def fetch(self, query: SearchQuery) -> list[RawJob]:
        params = {"limit": min(query.limit, 100)}
        if query.keywords:
            params["search"] = " ".join(query.keywords)
        try:
            resp = httpx.get(API_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        jobs: list[RawJob] = []
        for item in data.get("jobs", []):
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=item.get("title") or "",
                    company=item.get("company_name") or "",
                    location=item.get("candidate_required_location") or "Remote",
                    url=item.get("url") or "",
                    description=item.get("description") or "",
                    salary=item.get("salary") or "",
                    tags=item.get("tags") or [],
                    posted_at=_parse_iso(item.get("publication_date")),
                )
            )
        return jobs


def _parse_iso(value) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
