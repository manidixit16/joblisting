"""Offline, rule-based generator. No API key or network required.

Produces a clean, single-column, ATS-friendly resume and a personalized
cover letter by weaving the profile against keywords found in the job post.
"""
from __future__ import annotations

import re

from .base import DocumentGenerator, GeneratedDocuments, JobData, ProfileData

# Very small stopword list so keyword extraction stays dependency-free.
_STOPWORDS = {
    "the", "and", "for", "with", "you", "your", "our", "are", "will", "have",
    "this", "that", "from", "who", "job", "role", "team", "work", "working",
    "experience", "years", "a", "an", "to", "of", "in", "on", "as", "is", "we",
    "be", "or", "at", "by", "it", "all", "can", "not", "but", "they", "their",
}


def _extract_keywords(text: str, limit: int = 12) -> list[str]:
    words = re.findall(r"[A-Za-z][A-Za-z0-9+.#-]{2,}", (text or "").lower())
    freq: dict[str, int] = {}
    for w in words:
        if w in _STOPWORDS:
            continue
        freq[w] = freq.get(w, 0) + 1
    ranked = sorted(freq.items(), key=lambda kv: kv[1], reverse=True)
    return [w for w, _ in ranked[:limit]]


def _matched_skills(profile: ProfileData, job: JobData) -> list[str]:
    skills = [s.strip() for s in profile.skills.split(",") if s.strip()]
    jd = (job.description + " " + job.title).lower()
    matched = [s for s in skills if s.lower() in jd]
    # Keep some non-matched skills too so the resume isn't empty.
    remaining = [s for s in skills if s not in matched]
    return (matched + remaining)[:15]


class TemplateGenerator(DocumentGenerator):
    name = "template"

    def generate(self, profile: ProfileData, job: JobData) -> GeneratedDocuments:
        skills = _matched_skills(profile, job)
        keywords = _extract_keywords(job.description)

        resume = self._resume(profile, skills)
        cover = self._cover_letter(profile, job, skills, keywords)
        return GeneratedDocuments(resume=resume, cover_letter=cover, backend=self.name)

    def _resume(self, p: ProfileData, skills: list[str]) -> str:
        contact = " | ".join(x for x in [p.email, p.phone, p.location, p.links] if x)
        lines = [
            p.full_name or "Your Name",
            p.headline or "",
            contact,
            "",
            "SUMMARY",
            p.summary or "Motivated professional seeking a new opportunity.",
            "",
            "SKILLS",
            ", ".join(skills) if skills else p.skills,
            "",
            "EXPERIENCE",
            p.experience or "(Add your work experience in your profile.)",
            "",
            "EDUCATION",
            p.education or "(Add your education in your profile.)",
        ]
        return "\n".join(line for line in lines).strip() + "\n"

    def _cover_letter(
        self, p: ProfileData, job: JobData, skills: list[str], keywords: list[str]
    ) -> str:
        company = job.company or "your team"
        title = job.title or "the open role"
        skill_phrase = ", ".join(skills[:5]) if skills else "the required skills"
        focus = ", ".join(keywords[:4]) if keywords else "the goals of the role"
        name = p.full_name or "Your Name"

        return (
            f"Dear Hiring Team at {company},\n\n"
            f"I'm excited to apply for the {title} position. "
            f"{p.summary or 'I bring a track record of delivering results and learning quickly.'} "
            f"What drew me to this role is the focus on {focus}, which lines up closely "
            f"with the work I enjoy most.\n\n"
            f"In my experience I've applied {skill_phrase} to solve real problems and ship "
            f"outcomes that matter. I pay attention to detail, communicate clearly, and take "
            f"ownership of the work end to end. I'm confident I can do the same for {company}.\n\n"
            f"I'd welcome the chance to talk about how I can contribute. Thank you for your "
            f"time and consideration.\n\n"
            f"Sincerely,\n{name}\n"
        )
