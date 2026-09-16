"""Base interface + shared data for document generators."""
from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass
class ProfileData:
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


@dataclass
class JobData:
    title: str = ""
    company: str = ""
    location: str = ""
    description: str = ""
    url: str = ""


@dataclass
class GeneratedDocuments:
    resume: str
    cover_letter: str
    backend: str


class DocumentGenerator(ABC):
    """Produce a tailored, ATS-friendly resume and cover letter for a job."""

    name = "base"

    @abstractmethod
    def generate(self, profile: ProfileData, job: JobData) -> GeneratedDocuments:
        raise NotImplementedError
