"""RemoteOK source. Public JSON API: https://remoteok.com/api

RemoteOK returns remote jobs. First element of the array is metadata/legal
notice and is skipped. No applicant counts are exposed.
"""
from __future__ import annotations

from datetime import datetime, timezone

import httpx

from .base import JobSource, RawJob, SearchQuery

API_URL = "https://remoteok.com/api"


class RemoteOKSource(JobSource):
    name = "remoteok"

    def fetch(self, query: SearchQuery) -> list[RawJob]:
        headers = {"User-Agent": "joblisting-app/0.1 (personal job search)"}
        try:
            resp = httpx.get(API_URL, headers=headers, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        jobs: list[RawJob] = []
        for item in data:
            if not isinstance(item, dict) or "id" not in item:
                continue  # skip the leading legal/metadata element
            posted = _parse_epoch(item.get("epoch") or item.get("date"))
            tags = item.get("tags") or []
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=item.get("position") or item.get("title") or "",
                    company=item.get("company") or "",
                    location=item.get("location") or "Remote",
                    url=item.get("url") or item.get("apply_url") or "",
                    description=item.get("description") or "",
                    salary=_salary(item),
                    tags=[str(t) for t in tags],
                    posted_at=posted,
                )
            )
        return jobs


def _parse_epoch(value) -> datetime | None:
    if value is None:
        return None
    try:
        # RemoteOK gives an epoch int; `date` is ISO-ish as fallback.
        if isinstance(value, (int, float)) or str(value).isdigit():
            return datetime.fromtimestamp(int(value), tz=timezone.utc)
        return datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    except (ValueError, OSError, OverflowError):
        return None


def _salary(item: dict) -> str:
    lo, hi = item.get("salary_min"), item.get("salary_max")
    if lo and hi:
        return f"${int(lo):,} - ${int(hi):,}"
    return ""
