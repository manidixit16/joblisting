"""FastAPI application: routes for search, jobs, generation, review and send."""
from __future__ import annotations

import os
from contextlib import asynccontextmanager
from datetime import datetime, timedelta, timezone

from fastapi import Depends, FastAPI, HTTPException
from fastapi.responses import FileResponse, Response
from fastapi.staticfiles import StaticFiles
from sqlalchemy import select
from sqlalchemy.orm import Session

from .config import get_settings
from .database import get_session, init_db
from .models import Application, ApplicationStatus, Job, Profile, SearchConfig
from .schemas import (
    ApplicationOut,
    ApplicationUpdate,
    GenerateRequest,
    JobOut,
    ProfileIn,
    ProfileOut,
    RefreshRequest,
    RefreshResult,
    SearchConfigIn,
    SearchConfigOut,
    SendRequest,
)
from .services import aggregator
from .services.export import to_docx, to_pdf
from .services.generator import JobData, ProfileData, get_generator
from .services.sender import send_application
from .sources import SearchQuery, all_source_names

STATIC_DIR = os.path.join(os.path.dirname(__file__), "static")

@asynccontextmanager
async def lifespan(_: FastAPI):
    init_db()
    yield


app = FastAPI(title="AI Job Application Assistant", version="0.1.0", lifespan=lifespan)


# --------------------------------------------------------------------------- UI
@app.get("/")
def index() -> FileResponse:
    return FileResponse(os.path.join(STATIC_DIR, "index.html"))


@app.get("/api/health")
def health() -> dict:
    s = get_settings()
    return {
        "status": "ok",
        "generator_backend": s.generator_backend,
        "claude_available": s.claude_available,
        "email_dry_run": s.email_dry_run,
        "sources": all_source_names(),
    }


# ----------------------------------------------------------------------- Profile
def _get_or_create_profile(session: Session) -> Profile:
    profile = session.scalar(select(Profile).limit(1))
    if profile is None:
        profile = Profile()
        session.add(profile)
        session.commit()
    return profile


@app.get("/api/profile", response_model=ProfileOut)
def get_profile(session: Session = Depends(get_session)) -> Profile:
    return _get_or_create_profile(session)


@app.put("/api/profile", response_model=ProfileOut)
def update_profile(payload: ProfileIn, session: Session = Depends(get_session)) -> Profile:
    profile = _get_or_create_profile(session)
    for field, value in payload.model_dump().items():
        setattr(profile, field, value)
    session.commit()
    return profile


# ------------------------------------------------------------------ Search config
@app.get("/api/searches", response_model=list[SearchConfigOut])
def list_searches(session: Session = Depends(get_session)) -> list[SearchConfig]:
    return list(session.scalars(select(SearchConfig).order_by(SearchConfig.id.desc())))


@app.post("/api/searches", response_model=SearchConfigOut)
def create_search(payload: SearchConfigIn, session: Session = Depends(get_session)) -> SearchConfig:
    cfg = SearchConfig(**payload.model_dump())
    session.add(cfg)
    session.commit()
    return cfg


# ------------------------------------------------------------------------- Refresh
@app.post("/api/refresh", response_model=RefreshResult)
def refresh(payload: RefreshRequest, session: Session = Depends(get_session)) -> RefreshResult:
    keywords = [k.strip() for k in payload.keywords.split(",") if k.strip()]
    source_names = [s.strip() for s in payload.sources.split(",") if s.strip()]
    query = SearchQuery(
        keywords=keywords,
        location=payload.location,
        remote_only=payload.remote_only,
        max_age_hours=payload.max_age_hours or 24,
    )
    fresh_jobs = aggregator.collect(query, source_names or None)
    new_count, updated_count = aggregator.upsert_jobs(session, fresh_jobs)
    return RefreshResult(
        fetched=len(fresh_jobs),
        new=new_count,
        updated=updated_count,
        sources_used=source_names or all_source_names(),
    )


# ---------------------------------------------------------------------------- Jobs
@app.get("/api/jobs", response_model=list[JobOut])
def list_jobs(
    max_age_hours: int = 24,
    session: Session = Depends(get_session),
) -> list[Job]:
    cutoff = datetime.now(timezone.utc).replace(tzinfo=None) - timedelta(hours=max_age_hours)
    return list(
        session.scalars(
            select(Job).where(Job.posted_at >= cutoff).order_by(Job.posted_at.desc())
        )
    )


@app.get("/api/jobs/{job_id}", response_model=JobOut)
def get_job(job_id: int, session: Session = Depends(get_session)) -> Job:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    return job


# -------------------------------------------------------------------- Applications
def _to_out(app_obj: Application) -> Application:
    return app_obj


@app.post("/api/jobs/{job_id}/generate", response_model=ApplicationOut)
def generate_documents(
    job_id: int,
    payload: GenerateRequest,
    session: Session = Depends(get_session),
) -> Application:
    job = session.get(Job, job_id)
    if job is None:
        raise HTTPException(404, "Job not found")
    profile = _get_or_create_profile(session)

    generator = get_generator(payload.backend)
    docs = generator.generate(
        ProfileData(
            full_name=profile.full_name,
            email=profile.email,
            phone=profile.phone,
            location=profile.location,
            headline=profile.headline,
            summary=profile.summary,
            skills=profile.skills,
            experience=profile.experience,
            education=profile.education,
            links=profile.links,
        ),
        JobData(
            title=job.title,
            company=job.company,
            location=job.location,
            description=job.description,
            url=job.url,
        ),
    )

    application = session.scalar(select(Application).where(Application.job_id == job_id))
    if application is None:
        application = Application(job_id=job_id)
        session.add(application)
    application.resume = docs.resume
    application.cover_letter = docs.cover_letter
    application.generator = docs.backend
    application.status = ApplicationStatus.generated
    session.commit()
    return application


@app.get("/api/applications", response_model=list[ApplicationOut])
def list_applications(session: Session = Depends(get_session)) -> list[Application]:
    return list(session.scalars(select(Application).order_by(Application.updated_at.desc())))


@app.get("/api/applications/{app_id}", response_model=ApplicationOut)
def get_application(app_id: int, session: Session = Depends(get_session)) -> Application:
    application = session.get(Application, app_id)
    if application is None:
        raise HTTPException(404, "Application not found")
    return application


@app.put("/api/applications/{app_id}", response_model=ApplicationOut)
def update_application(
    app_id: int,
    payload: ApplicationUpdate,
    session: Session = Depends(get_session),
) -> Application:
    application = session.get(Application, app_id)
    if application is None:
        raise HTTPException(404, "Application not found")
    if payload.resume is not None:
        application.resume = payload.resume
    if payload.cover_letter is not None:
        application.cover_letter = payload.cover_letter
    if payload.notes is not None:
        application.notes = payload.notes
    if payload.status is not None:
        try:
            application.status = ApplicationStatus(payload.status)
        except ValueError:
            raise HTTPException(400, f"Invalid status: {payload.status}")
    session.commit()
    return application


_DOC_FIELDS = {"resume": "resume", "cover_letter": "cover_letter"}
_MIME = {
    "pdf": "application/pdf",
    "docx": "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
}


@app.get("/api/applications/{app_id}/{doc}.{fmt}")
def download_document(
    app_id: int,
    doc: str,
    fmt: str,
    session: Session = Depends(get_session),
) -> Response:
    """Download a generated document as PDF or DOCX.

    doc: 'resume' | 'cover_letter'   fmt: 'pdf' | 'docx'
    """
    if doc not in _DOC_FIELDS:
        raise HTTPException(404, "Unknown document. Use 'resume' or 'cover_letter'.")
    if fmt not in _MIME:
        raise HTTPException(404, "Unsupported format. Use 'pdf' or 'docx'.")

    application = session.get(Application, app_id)
    if application is None:
        raise HTTPException(404, "Application not found")

    text = getattr(application, _DOC_FIELDS[doc])
    if not text:
        raise HTTPException(409, f"No {doc.replace('_', ' ')} generated yet.")

    job = session.get(Job, application.job_id)
    title = f"{doc} - {job.title if job else 'application'}"
    data = to_pdf(text, title) if fmt == "pdf" else to_docx(text, title)
    filename = f"{doc}_{app_id}.{fmt}"
    return Response(
        content=data,
        media_type=_MIME[fmt],
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


@app.post("/api/applications/{app_id}/send", response_model=ApplicationOut)
def send(
    app_id: int,
    payload: SendRequest,
    session: Session = Depends(get_session),
) -> Application:
    application = session.get(Application, app_id)
    if application is None:
        raise HTTPException(404, "Application not found")

    # Human-in-the-loop gate: only approved applications may be sent.
    if application.status != ApplicationStatus.approved:
        raise HTTPException(
            409,
            "Application must be reviewed and set to 'approved' before it can be sent.",
        )

    job = session.get(Job, application.job_id)
    to_email = (payload.to_email or (job.apply_email if job else "")).strip()
    if not to_email:
        raise HTTPException(
            422,
            "No recipient email for this job. Add one via the send form (many jobs "
            "require applying through their website instead of email).",
        )

    subject = payload.subject or f"Application: {job.title} at {job.company}" if job else "Application"
    body = payload.body or application.cover_letter

    result = send_application(
        to_email=to_email,
        subject=subject,
        body=body,
        resume=application.resume,
        cover_letter=application.cover_letter,
    )
    if not result.delivered:
        raise HTTPException(502, result.detail)

    application.status = ApplicationStatus.sent
    application.sent_to = to_email
    application.sent_at = datetime.now(timezone.utc).replace(tzinfo=None)
    application.notes = (application.notes + "\n" + result.detail).strip()
    session.commit()
    return application


# Mount static files last so /api routes take precedence.
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
