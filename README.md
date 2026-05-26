# Reporting App

A locally-run web UI that collects entries (files, emails, free text), deduplicates them, and generates weekly/monthly reports on demand.

## Quick Start

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=sk-...   # optional — summaries are skipped if absent
uvicorn backend.main:app --reload --port 8000
```

Then open **http://localhost:8000** in your browser.

## Features

- **Add Entry** — paste a note, paste an email, or upload a file (`.txt`, `.pdf`, `.docx`, `.eml`, `.csv`, `.md`)
- **Deduplication** — exact duplicates are rejected at ingestion time (SHA-256 on normalised content)
- **Browse** — filter entries by type and date range; delete individual entries
- **Weekly Report** — generates a `.md` file covering the last 7 days (or a custom range)
- **Monthly Report** — fills your custom template with entries and AI summaries
- **AI Summaries** — one-sentence summaries via `claude-haiku-4-5-20251001`; skipped gracefully if no API key is set

## Monthly Template

A default template is included at `templates/monthly_report_template.md`. Replace it via the **Template** tab in the UI.

Supported placeholder tokens:

| Token | Replaced with |
|-------|---------------|
| `{{month}}` | Month and year (e.g. "May 2026") |
| `{{entries}}` | Bulleted list of all entries for the month |
| `{{summary}}` | One-sentence AI summary of all entries |
| `{{topic_summary}}` | Per-tag AI summaries |

Supported template formats: `.md`, `.html`, `.docx`

## Project Structure

```
backend/          Python/FastAPI backend
  main.py         API routes + app entry point
  ingestion.py    Text extraction from files and emails
  dedup.py        SHA-256 deduplication
  storage.py      SQLite persistence (SQLAlchemy)
  models.py       Pydantic and ORM models
  reports/
    weekly.py     Weekly .md report generator
    monthly.py    Monthly template-based report generator
frontend/         Vanilla HTML/JS/CSS single-page UI
templates/        Monthly report template (upload your own)
data/             SQLite DB + uploaded files (created on first run)
reports/          Generated report files (immutable snapshots)
```

## Notes

- All data is local. The only external call is the Anthropic API for summarisation.
- Reports are never overwritten — each generation appends a timestamp to the filename.
- See `SPEC.md` for implementation decisions and open questions.
