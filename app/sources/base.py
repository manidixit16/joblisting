"""Base types for job sources.

A *source* is an adapter around a legal job-board API/feed. Each source
returns a list of `RawJob` objects; the aggregator normalizes, filters
(24h freshness, keyword match) and de-duplicates across sources.
"""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime


@dataclass
class SearchQuery:
    keywords: list[str] = field(default_factory=list)
    location: str = ""
    remote_only: bool = False
    max_age_hours: int = 24
    limit: int = 100


@dataclass
class RawJob:
    source: str
    external_id: str
    title: str
    company: str = ""
    location: str = ""
    url: str = ""
    description: str = ""
    salary: str = ""
    tags: list[str] = field(default_factory=list)
    apply_email: str = ""
    # Only populated by sources that expose it (most do not).
    applicants: int | None = None
    posted_at: datetime | None = None  # must be timezone-aware UTC when set


class JobSource(ABC):
    """Interface every source adapter implements."""

    name: str = "base"

    @abstractmethod
    def fetch(self, query: SearchQuery) -> list[RawJob]:
        """Return raw listings for the query. Should not raise on empty results."""
        raise NotImplementedError
