"""Claude-backed generator. Produces human-sounding, ATS-friendly documents.

Requires ANTHROPIC_API_KEY. Falls back is handled by the factory, not here.
"""
from __future__ import annotations

from ...config import get_settings
from .base import DocumentGenerator, GeneratedDocuments, JobData, ProfileData

_SYSTEM = (
    "You are an expert career writer. You write resumes and cover letters that "
    "are ATS-friendly (plain text, standard section headings, real keywords from "
    "the job description, no tables/columns/graphics) yet sound genuinely human, "
    "specific, and warm — never robotic or clichéd. Never invent facts, "
    "employers, degrees, or metrics that are not supported by the candidate's "
    "profile. If information is missing, write honestly around it."
)

_RESUME_PROMPT = """Write a tailored, ATS-friendly resume in plain text for this candidate and job.

Rules:
- Use standard headings: SUMMARY, SKILLS, EXPERIENCE, EDUCATION.
- Mirror real keywords from the job description where the candidate genuinely matches.
- Single column, no tables, no special characters for layout.
- Do not fabricate anything not present in the profile.

CANDIDATE PROFILE:
{profile}

JOB:
{job}

Return ONLY the resume text."""

_COVER_PROMPT = """Write a tailored cover letter for this candidate and job.

Rules:
- Human, warm, specific, and concise (250-350 words).
- Reference the company and role and 2-3 real, matching strengths.
- ATS-friendly plain text, no headers/graphics.
- Do not fabricate experience. Sign off with the candidate's name.

CANDIDATE PROFILE:
{profile}

JOB:
{job}

Return ONLY the cover letter text."""


def _fmt_profile(p: ProfileData) -> str:
    return (
        f"Name: {p.full_name}\nHeadline: {p.headline}\nLocation: {p.location}\n"
        f"Summary: {p.summary}\nSkills: {p.skills}\nExperience: {p.experience}\n"
        f"Education: {p.education}\nLinks: {p.links}"
    )


def _fmt_job(j: JobData) -> str:
    return f"Title: {j.title}\nCompany: {j.company}\nLocation: {j.location}\nDescription: {j.description}"


class ClaudeGenerator(DocumentGenerator):
    name = "claude"

    def generate(self, profile: ProfileData, job: JobData) -> GeneratedDocuments:
        # Imported lazily so the package is optional.
        from anthropic import Anthropic

        s = get_settings()
        client = Anthropic(api_key=s.anthropic_api_key)
        p, j = _fmt_profile(profile), _fmt_job(job)

        resume = self._complete(client, s.anthropic_model, _RESUME_PROMPT.format(profile=p, job=j))
        cover = self._complete(client, s.anthropic_model, _COVER_PROMPT.format(profile=p, job=j))
        return GeneratedDocuments(resume=resume, cover_letter=cover, backend=self.name)

    def _complete(self, client, model: str, prompt: str) -> str:
        msg = client.messages.create(
            model=model,
            max_tokens=2000,
            system=_SYSTEM,
            messages=[{"role": "user", "content": prompt}],
        )
        parts = [block.text for block in msg.content if getattr(block, "type", "") == "text"]
        return "\n".join(parts).strip()
