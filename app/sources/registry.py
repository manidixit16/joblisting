"""Registry of available job sources."""
from __future__ import annotations

from .adzuna import AdzunaSource
from .base import JobSource
from .hackernews import HackerNewsSource
from .remoteok import RemoteOKSource
from .remotive import RemotiveSource

# Order roughly by usefulness for a keyword search.
_SOURCES: dict[str, JobSource] = {
    RemotiveSource.name: RemotiveSource(),
    RemoteOKSource.name: RemoteOKSource(),
    HackerNewsSource.name: HackerNewsSource(),
    AdzunaSource.name: AdzunaSource(),
}


def all_source_names() -> list[str]:
    return list(_SOURCES.keys())


def get_sources(names: list[str] | None = None) -> list[JobSource]:
    """Return source instances. Empty/None `names` => all sources."""
    if not names:
        return list(_SOURCES.values())
    return [_SOURCES[n] for n in names if n in _SOURCES]
