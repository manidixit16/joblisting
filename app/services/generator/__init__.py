"""Pluggable document generators (template + Claude)."""
from .base import DocumentGenerator, GeneratedDocuments, JobData, ProfileData
from .factory import get_generator

__all__ = [
    "DocumentGenerator",
    "GeneratedDocuments",
    "JobData",
    "ProfileData",
    "get_generator",
]
