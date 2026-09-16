"""Hacker News "Who is hiring?" source via the Algolia HN Search API.

Fetches recent comments (each comment is typically one job post) from the
monthly "Ask HN: Who is hiring?" threads. Applicant counts are not available.
"""
from __future__ import annotations

import re
from datetime import datetime, timezone

import httpx

from .base import JobSource, RawJob, SearchQuery

SEARCH_URL = "https://hn.algolia.com/api/v1/search_by_date"
EMAIL_RE = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")


class HackerNewsSource(JobSource):
    name = "hackernews"

    def fetch(self, query: SearchQuery) -> list[RawJob]:
        # Restrict to recent "who is hiring" comments.
        params = {
            "tags": "comment",
            "query": "who is hiring",
            "hitsPerPage": min(query.limit, 100),
        }
        try:
            resp = httpx.get(SEARCH_URL, params=params, timeout=20)
            resp.raise_for_status()
            data = resp.json()
        except Exception:
            return []

        jobs: list[RawJob] = []
        for hit in data.get("hits", []):
            text = _strip_html(hit.get("comment_text") or "")
            if not text:
                continue
            first_line = text.split("\n", 1)[0][:200]
            emails = EMAIL_RE.findall(text)
            jobs.append(
                RawJob(
                    source=self.name,
                    external_id=str(hit.get("objectID")),
                    title=first_line or "HN job post",
                    company=hit.get("author") or "",
                    location="",
                    url=f"https://news.ycombinator.com/item?id={hit.get('objectID')}",
                    description=text,
                    apply_email=emails[0] if emails else "",
                    posted_at=_parse_created(hit),
                )
            )
        return jobs


def _strip_html(html: str) -> str:
    text = re.sub(r"<[^>]+>", " ", html)
    text = (
        text.replace("&#x2F;", "/")
        .replace("&gt;", ">")
        .replace("&lt;", "<")
        .replace("&amp;", "&")
        .replace("&#x27;", "'")
        .replace("&quot;", '"')
    )
    return re.sub(r"[ \t]+", " ", text).strip()


def _parse_created(hit: dict) -> datetime | None:
    ts = hit.get("created_at_i")
    if ts is not None:
        try:
            return datetime.fromtimestamp(int(ts), tz=timezone.utc)
        except (ValueError, OSError, OverflowError):
            pass
    created = hit.get("created_at")
    if created:
        try:
            return datetime.fromisoformat(str(created).replace("Z", "+00:00"))
        except ValueError:
            return None
    return None
