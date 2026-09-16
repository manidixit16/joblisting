# AI Job Application Assistant

Find **fresh (≤24h) job listings** from legal job-board APIs, generate a
**tailored, ATS-friendly resume and cover letter** for each one, then
**review and approve** every application before anything is ever sent.

> Human-in-the-loop by design: the app drafts everything for you, but **nothing
> is emailed until you review it and mark it `approved`.**

---

## What it does today (MVP)

- 🔎 **Aggregated search** across multiple sources: Remotive, RemoteOK,
  Hacker News "Who's hiring?", and Adzuna (if you add a free API key).
- ⏱ **24-hour freshness filter** — only recent listings; anything with an
  unknown post date is excluded so the "≤24h" promise holds.
- 🧮 **Applicant counts** shown when a source exposes them (most public APIs
  don't; those show `N/A`). See [Applicant counts](#applicant-counts).
- ✍️ **Tailored documents** via a **pluggable generator**:
  - `template` — offline, no API key, rule-based (matches your skills to the JD).
  - `claude` — Anthropic Claude API for human-sounding, ATS-friendly writing.
  - `auto` — uses Claude if a key is present, otherwise falls back to template.
- ✅ **Review workflow** — edit the drafts, approve, then send.
- 📧 **Safe sending** — SMTP email that defaults to **dry-run** (writes `.eml`
  files to `./outbox/` so you can verify before going live).
- 🖥 **Simple web UI** at `/` for the whole loop: search → generate → review → send.

## Quick start

```bash
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env          # optional: add keys/SMTP; defaults work as-is
python run.py                 # open http://127.0.0.1:8000
```

1. Open the app, go to **Profile**, and fill in your details (this is the only
   source of truth — the generator never fabricates beyond what you enter).
2. Go to **Search**, enter keywords, and click **Fetch jobs**.
3. Click **Generate application** on a job.
4. Go to **Review & Apply**, edit if needed, click **Approve**, then **Send**
   (dry-run by default).

## Configuration

All settings live in `.env` (see `.env.example`). Highlights:

| Variable | Purpose | Default |
|---|---|---|
| `GENERATOR_BACKEND` | `auto` / `claude` / `template` | `auto` |
| `ANTHROPIC_API_KEY` | enables the Claude backend | *(empty)* |
| `ADZUNA_APP_ID` / `ADZUNA_APP_KEY` | enable the Adzuna source | *(empty)* |
| `EMAIL_DRY_RUN` | `true` writes `.eml` to `./outbox` instead of sending | `true` |
| `SMTP_*`, `FROM_EMAIL` | live email delivery | *(empty)* |
| `DATABASE_URL` | storage | local SQLite |

## Testing

```bash
pytest -q
```

Tests run fully offline (sources are mocked; email is dry-run).

## Architecture

```
app/
  config.py            settings (.env)
  database.py          SQLAlchemy engine/session
  models.py            Profile, SearchConfig, Job, Application
  schemas.py           Pydantic request/response models
  main.py              FastAPI routes + lifespan
  sources/             job-source adapters (base + registry)
    remotive.py remoteok.py hackernews.py adzuna.py
  services/
    aggregator.py      freshness filter, keyword match, dedup, persistence
    generator/         pluggable resume/cover generation
      template.py claude.py factory.py
    sender.py          approval-gated, dry-run-safe email
  static/index.html    single-page review UI
tests/                 aggregator, generator, and end-to-end API tests
```

### Adding a job source

Create `app/sources/<name>.py` with a class that subclasses `JobSource`,
implement `fetch(query) -> list[RawJob]`, and register it in
`app/sources/registry.py`. The aggregator handles freshness, keywords and
dedup for you.

## Legal & ethical notes

- This tool uses **official APIs and public feeds**. It does **not** scrape
  sites (e.g. LinkedIn, Indeed) whose Terms of Service forbid it — that path
  gets you IP-banned and can carry legal risk.
- **Auto-applying is intentionally gated** behind your explicit approval to
  avoid spamming employers. Please keep applications genuine and relevant.
- Respect each source's rate limits and terms.

### Applicant counts

"How many people applied" is only published by a few sources (notably
LinkedIn, which we don't scrape). Where a source exposes it we store and show
it; otherwise the UI shows `N/A`. The data model already has an `applicants`
field, so a future compliant source can populate it.

## Roadmap / not yet built

- More sources via official APIs/feeds (Greenhouse, Lever, USAJOBS, Jooble).
- Auto-fill of web application **forms** (currently email-only; forms vary too
  much per site to do safely without per-site adapters + your review).
- Scheduled background refresh + notifications for new matches.
- PDF/DOCX export of resumes and cover letters.
- Per-search saved profiles and multiple resume variants.

---

Generated with [Claude Code](https://claude.com/claude-code).
