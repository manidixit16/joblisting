"""Adzuna source. Free API (register at https://developer.adzuna.com).

Requires ADZUNA_APP_ID and ADZUNA_APP_KEY. Supports keyword + location and a
`max_days_old` filter. Returns broad (not remote-only) listings.
"""
from __future__ import annotations

from datetime import datetime, timezone
from math import ceil

import httpx

from ..config import get_settings
from .base import JobSource, RawJob, SearchQuery


class AdzunaSource(JobSource):
    name = "adzuna"

    def fetch(self, query: SearchQuery) -> list[RawJob]:
        s = get_settings()
        if not (s.adzuna_app_id and s.adzuna_app_key):
            return []  # not configured; silently skip

        country = s.adzuna_country or "us"
        url = f"https://api.adzuna.com/v1/api/jobs/{country}/search/1"
        params = {
            "app_id": s.adzuna_app_id,
            "app_key": s.adzuna_app_key,
            "results_per_page": min(query.limit, 50),
            "max_days_old": max(1, ceil(query.max_age_hours / 24)),
            "content-type": "application/json",
        }
        if query.keywords:
            params["what"] = " ".join(query.keywords)
        if query.location:
            params["where"] = query.location

        try:
            resp = httpx.get(url, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        jobs: list[RawJob] = []
        for item in data.get("results", []):
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(item.get("id")),
                    title=item.get("title") or "",
                    company=(item.get("company") or {}).get("display_name") or "",
                    location=(item.get("location") or {}).get("display_name") or "",
                    url=item.get("redirect_url") or "",
                    description=item.get("description") or "",
                    salary=_salary(item),
                    tags=[(item.get("category") or {}).get("label") or ""],
                    posted_at=_parse_iso(item.get("created")),
                )
            )
        return jobs


def _salary(item: dict) -> str:
    lo, hi = item.get("salary_min"), item.get("salary_max")
    if lo and hi:
        return f"{int(lo):,} - {int(hi):,}"
    return ""


def _parse_iso(value) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)
    except ValueError:
        return None
