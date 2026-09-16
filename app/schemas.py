"""Pydantic request/response schemas for the API."""
from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, ConfigDict


class ProfileIn(BaseModel):
    full_name: str = ""
    email: str = ""
    phone: str = ""
    location: str = ""
    headline: str = ""
    summary: str = ""
    skills: str = ""
    experience: str = ""
    education: str = ""
    links: str = ""


class ProfileOut(ProfileIn):
    model_config = ConfigDict(from_attributes=True)
    id: int


class SearchConfigIn(BaseModel):
    name: str = "My search"
    keywords: str = ""
    location: str = ""
    remote_only: bool = False
    max_age_hours: int = 24
    sources: str = ""


class SearchConfigOut(SearchConfigIn):
    model_config = ConfigDict(from_attributes=True)
    id: int
    is_active: bool


class RefreshRequest(BaseModel):
    keywords: str = ""
    location: str = ""
    remote_only: bool = False
    max_age_hours: int = 24
    sources: str = ""  # comma separated; empty = all


class RefreshResult(BaseModel):
    fetched: int
    new: int
    updated: int
    sources_used: list[str]


class JobOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    source: str
    title: str
    company: str
    location: str
    url: str
    salary: str
    tags: str
    apply_email: str
    applicants: int | None
    posted_at: datetime


class ApplicationOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: int
    job_id: int
    status: str
    resume: str
    cover_letter: str
    generator: str
    notes: str
    sent_to: str
    sent_at: datetime | None


class GenerateRequest(BaseModel):
    backend: str | None = None  # override: template | claude | auto


class ApplicationUpdate(BaseModel):
    resume: str | None = None
    cover_letter: str | None = None
    notes: str | None = None
    status: str | None = None


class SendRequest(BaseModel):
    to_email: str | None = None  # override recipient if the job has none
    subject: str | None = None
    body: str | None = None
