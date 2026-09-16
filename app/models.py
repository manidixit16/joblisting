"""ORM models: Profile, SearchConfig, Job, Application."""
from __future__ import annotations

import enum
from datetime import datetime, timezone

from sqlalchemy import (
    DateTime,
    Enum,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


def _utcnow() -> datetime:
    return datetime.now(timezone.utc)


class ApplicationStatus(str, enum.Enum):
    """Lifecycle of an application. Nothing is sent before `approved`."""

    draft = "draft"          # created, no documents yet
    generated = "generated"  # resume + cover letter generated, awaiting review
    approved = "approved"    # applicant reviewed & approved -> eligible to send
    sent = "sent"            # delivered (or written to outbox in dry-run)
    rejected = "rejected"    # applicant chose not to apply


class Profile(Base):
    """The applicant's master profile used to tailor every document."""

    __tablename__ = "profiles"

    id: Mapped[int] = mapped_column(primary_key=True)
    full_name: Mapped[str] = mapped_column(String(200), default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(50), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    headline: Mapped[str] = mapped_column(String(300), default="")
    summary: Mapped[str] = mapped_column(Text, default="")
    skills: Mapped[str] = mapped_column(Text, default="")          # comma separated
    experience: Mapped[str] = mapped_column(Text, default="")      # free text / markdown
    education: Mapped[str] = mapped_column(Text, default="")
    links: Mapped[str] = mapped_column(Text, default="")           # portfolio/github/linkedin
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)


class SearchConfig(Base):
    """A saved job search. The aggregator uses these to fetch listings."""

    __tablename__ = "search_configs"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(200), default="My search")
    keywords: Mapped[str] = mapped_column(Text, default="")   # comma separated
    location: Mapped[str] = mapped_column(String(200), default="")
    remote_only: Mapped[bool] = mapped_column(default=False)
    max_age_hours: Mapped[int] = mapped_column(Integer, default=24)
    sources: Mapped[str] = mapped_column(Text, default="")    # comma separated; empty = all
    is_active: Mapped[bool] = mapped_column(default=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)


class Job(Base):
    """A normalized job listing fetched from a source."""

    __tablename__ = "jobs"
    __table_args__ = (UniqueConstraint("source", "external_id", name="uq_source_extid"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(50), index=True)
    external_id: Mapped[str] = mapped_column(String(200))
    title: Mapped[str] = mapped_column(String(300))
    company: Mapped[str] = mapped_column(String(200), default="")
    location: Mapped[str] = mapped_column(String(200), default="")
    url: Mapped[str] = mapped_column(Text, default="")
    description: Mapped[str] = mapped_column(Text, default="")
    salary: Mapped[str] = mapped_column(String(200), default="")
    tags: Mapped[str] = mapped_column(Text, default="")           # comma separated
    apply_email: Mapped[str] = mapped_column(String(200), default="")
    # Applicant count: only some sources expose this (e.g. LinkedIn). NULL = unknown.
    applicants: Mapped[int | None] = mapped_column(Integer, nullable=True)
    posted_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    fetched_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)

    applications: Mapped[list["Application"]] = relationship(back_populates="job")


class Application(Base):
    """A generated application for a job, reviewed and approved by the user."""

    __tablename__ = "applications"

    id: Mapped[int] = mapped_column(primary_key=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id"))
    status: Mapped[ApplicationStatus] = mapped_column(
        Enum(ApplicationStatus), default=ApplicationStatus.draft, index=True
    )
    resume: Mapped[str] = mapped_column(Text, default="")
    cover_letter: Mapped[str] = mapped_column(Text, default="")
    generator: Mapped[str] = mapped_column(String(50), default="")  # which backend produced it
    notes: Mapped[str] = mapped_column(Text, default="")
    sent_to: Mapped[str] = mapped_column(String(200), default="")
    sent_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_utcnow, onupdate=_utcnow)

    job: Mapped["Job"] = relationship(back_populates="applications")
