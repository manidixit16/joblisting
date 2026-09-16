"""Tests for the pluggable document generator."""
from app.services.generator import JobData, ProfileData, get_generator
from app.services.generator.template import TemplateGenerator


def _profile():
    return ProfileData(
        full_name="Jane Doe",
        email="jane@example.com",
        headline="Backend Engineer",
        summary="Backend engineer with 5 years building APIs.",
        skills="Python, FastAPI, PostgreSQL, Docker, AWS",
        experience="Built payment systems at Acme.",
        education="BS Computer Science",
    )


def _job():
    return JobData(
        title="Senior Python Engineer",
        company="Globex",
        description="Looking for Python and FastAPI experts to build scalable APIs.",
    )


def test_template_generator_produces_both_docs():
    docs = TemplateGenerator().generate(_profile(), _job())
    assert "Jane Doe" in docs.resume
    assert "SKILLS" in docs.resume
    assert "Globex" in docs.cover_letter
    assert "Senior Python Engineer" in docs.cover_letter
    assert docs.backend == "template"


def test_template_prioritizes_matching_skills():
    docs = TemplateGenerator().generate(_profile(), _job())
    # Python and FastAPI appear in the job description, so they should be present.
    assert "Python" in docs.resume
    assert "FastAPI" in docs.resume


def test_factory_falls_back_to_template_without_key(monkeypatch):
    import app.services.generator.factory as f

    class NoKey:
        generator_backend = "auto"
        claude_available = False

    monkeypatch.setattr(f, "get_settings", lambda: NoKey())
    gen = get_generator("auto")
    assert isinstance(gen, TemplateGenerator)


def test_factory_explicit_template():
    assert isinstance(get_generator("template"), TemplateGenerator)
