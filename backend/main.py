import os
import re
import shutil
from datetime import datetime
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv
load_dotenv(Path(__file__).parent.parent / ".env")

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
from sqlalchemy.orm import Session

from .dedup import compute_hash
from .ingestion import ALLOWED_SUFFIXES, extract_text_from_file, parse_email_paste
from .models import EntryCreate, EntryResponse, EntryType
from .storage import (
    create_entry,
    delete_entry,
    get_db,
    get_entries,
    hash_exists,
    init_db,
)

UPLOADS_DIR = Path("data/uploads")
UPLOADS_DIR.mkdir(parents=True, exist_ok=True)
TEMPLATES_DIR = Path("templates")
TEMPLATES_DIR.mkdir(exist_ok=True)
REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)
FINALS_DIR = REPORTS_DIR / "finals"
FINALS_DIR.mkdir(exist_ok=True)

app = FastAPI(title="Reporting App", version="1.0.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


# ---------------------------------------------------------------------------
# Entries
# ---------------------------------------------------------------------------


class CleanupRequest(BaseModel):
    content: str


@app.post("/entries/cleanup")
def cleanup_entry(req: CleanupRequest):
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise HTTPException(status_code=503, detail="API key not configured.")
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[{"role": "user", "content": (
                "Clean up the following text. Remove filler words, false starts, "
                "incomplete sentences, verbal corrections, and repetitions. "
                "Preserve all factual content, names, numbers, and business information. "
                "Return only the cleaned text, no explanation.\n\n" + req.content
            )}],
        )
        return {"content": msg.content[0].text.strip()}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc))


class TextEntryRequest(BaseModel):
    content: str
    source: str = "manual"
    type: EntryType = EntryType.text
    date_stamp: Optional[datetime] = None
    tags: list[str] = []


@app.post("/entries", response_model=EntryResponse, status_code=201)
def submit_entry(req: TextEntryRequest, db: Session = Depends(get_db)):
    h = compute_hash(req.content)
    if hash_exists(db, h):
        raise HTTPException(
            status_code=409,
            detail="Duplicate entry: this content has already been submitted.",
        )
    entry = create_entry(
        db,
        EntryCreate(
            type=req.type,
            content=req.content,
            source=req.source,
            date_stamp=req.date_stamp,
            tags=req.tags,
        ),
        h,
    )
    return EntryResponse.model_validate(entry)


@app.post("/entries/upload", response_model=EntryResponse, status_code=201)
async def upload_file(
    file: UploadFile = File(...),
    date_stamp: Optional[str] = Form(None),
    tags: Optional[str] = Form(None),
    db: Session = Depends(get_db),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in ALLOWED_SUFFIXES:
        raise HTTPException(
            status_code=400, detail=f"Unsupported file type '{suffix}'. "
            f"Allowed: {', '.join(sorted(ALLOWED_SUFFIXES))}"
        )

    save_path = UPLOADS_DIR / file.filename
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    content, source = extract_text_from_file(save_path, file.filename)
    if not content.strip():
        save_path.unlink(missing_ok=True)
        raise HTTPException(status_code=422, detail="Could not extract text from the uploaded file.")

    entry_type = EntryType.email if suffix == ".eml" else EntryType.file

    h = compute_hash(content)
    if hash_exists(db, h):
        save_path.unlink(missing_ok=True)
        raise HTTPException(
            status_code=409,
            detail="Duplicate entry: this content has already been submitted.",
        )

    parsed_date: Optional[datetime] = None
    if date_stamp:
        try:
            parsed_date = datetime.fromisoformat(date_stamp)
        except ValueError:
            pass

    tag_list = [t.strip() for t in (tags or "").split(",") if t.strip()]

    entry = create_entry(
        db,
        EntryCreate(
            type=entry_type,
            content=content,
            source=source,
            date_stamp=parsed_date,
            tags=tag_list,
        ),
        h,
    )
    return EntryResponse.model_validate(entry)


@app.get("/entries", response_model=list[EntryResponse])
def list_entries(
    type: Optional[str] = None,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
    db: Session = Depends(get_db),
):
    start = datetime.fromisoformat(start_date) if start_date else None
    end = datetime.fromisoformat(end_date) if end_date else None
    entries = get_entries(db, type_filter=type, start_date=start, end_date=end)
    return [EntryResponse.model_validate(e) for e in entries]


@app.delete("/entries/{entry_id}")
def remove_entry(entry_id: str, db: Session = Depends(get_db)):
    if not delete_entry(db, entry_id):
        raise HTTPException(status_code=404, detail="Entry not found.")
    return {"ok": True}


# ---------------------------------------------------------------------------
# Reports
# ---------------------------------------------------------------------------


class IntermediateReportRequest(BaseModel):
    start_date: Optional[datetime] = None
    end_date: Optional[datetime] = None


@app.post("/reports/intermediate")
def generate_intermediate(
    req: IntermediateReportRequest = IntermediateReportRequest(),
    db: Session = Depends(get_db),
):
    from .reports.intermediate import generate_intermediate_report

    entries = get_entries(db)
    output_path = generate_intermediate_report(entries, req.start_date, req.end_date)
    return {"filename": output_path.name}


class MonthlyReportRequest(BaseModel):
    year: int
    month: int


@app.post("/reports/monthly")
def generate_monthly(req: MonthlyReportRequest, db: Session = Depends(get_db)):
    from .reports.monthly import generate_monthly_report

    try:
        entries = get_entries(db)
        output_path = generate_monthly_report(entries, req.year, req.month)
        return {"filename": output_path.name}
    except FileNotFoundError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))


@app.get("/reports")
def list_reports():
    files = sorted(REPORTS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    return [
        {"filename": f.name, "size": f.stat().st_size}
        for f in files
        if f.is_file()
    ]


# ---------------------------------------------------------------------------
# Final reports
# ---------------------------------------------------------------------------

FINALS_ALLOWED = {".md", ".html", ".docx"}


@app.post("/reports/finals")
async def upload_final(
    file: UploadFile = File(...),
    year: int = Form(...),
    month: int = Form(...),
):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in FINALS_ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported format '{suffix}'. Allowed: .md, .html, .docx",
        )
    for ext in FINALS_ALLOWED:
        (FINALS_DIR / f"monthly_{year}-{month:02d}_final{ext}").unlink(missing_ok=True)
    save_path = FINALS_DIR / f"monthly_{year}-{month:02d}_final{suffix}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True, "filename": save_path.name}


@app.get("/reports/finals")
def list_finals():
    from .reports.compare import find_latest_generated
    files = sorted(FINALS_DIR.iterdir(), key=lambda p: p.stat().st_mtime, reverse=True)
    result = []
    for f in files:
        if not f.is_file():
            continue
        m = re.match(r"monthly_(\d{4})-(\d{2})_final\.\w+", f.name)
        year = int(m.group(1)) if m else None
        month = int(m.group(2)) if m else None
        has_generated = bool(find_latest_generated(year, month)) if year and month else False
        result.append({
            "filename": f.name,
            "size": f.stat().st_size,
            "year": year,
            "month": month,
            "has_generated": has_generated,
        })
    return result


@app.get("/reports/finals/{filename}")
def download_final(filename: str):
    p = FINALS_DIR / filename
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Final report not found.")
    return FileResponse(str(p), filename=filename)


@app.delete("/reports/finals/{filename}")
def delete_final(filename: str):
    p = FINALS_DIR / filename
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Final report not found.")
    p.unlink()
    return {"ok": True}


class ApplyLessonsRequest(BaseModel):
    lessons: list[str]


@app.post("/reports/learn/{year}/{month}")
def compare_reports(year: int, month: int):
    from .reports.compare import extract_lessons
    result = extract_lessons(year, month)
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
    return result


@app.post("/reports/learn/{year}/{month}/apply")
def apply_lessons(year: int, month: int, req: ApplyLessonsRequest):
    if not req.lessons:
        raise HTTPException(status_code=400, detail="No lessons provided.")
    style_path = Path("REPORT_STYLE.md")
    month_label = f"{year}-{month:02d}"
    lines = [f"\n\n## Lessons — {month_label}\n"]
    for lesson in req.lessons:
        lines.append(f"- {lesson.strip()}\n")
    with open(style_path, "a", encoding="utf-8") as f:
        f.writelines(lines)
    return {"ok": True, "appended": len(req.lessons)}


@app.get("/reports/{filename}")
def download_report(filename: str):
    p = REPORTS_DIR / filename
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Report not found.")
    return FileResponse(str(p), filename=filename)


@app.delete("/reports/{filename}")
def delete_report(filename: str):
    p = REPORTS_DIR / filename
    if not p.exists() or not p.is_file():
        raise HTTPException(status_code=404, detail="Report not found.")
    p.unlink()
    return {"ok": True}


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

TEMPLATE_ALLOWED = {".md", ".html", ".docx"}


@app.post("/templates/monthly")
async def upload_template(file: UploadFile = File(...)):
    suffix = Path(file.filename).suffix.lower()
    if suffix not in TEMPLATE_ALLOWED:
        raise HTTPException(
            status_code=400,
            detail=f"Unsupported template format '{suffix}'. Allowed: .md, .html, .docx",
        )
    for old in TEMPLATES_DIR.glob("monthly_report_template.*"):
        old.unlink()
    save_path = TEMPLATES_DIR / f"monthly_report_template{suffix}"
    with open(save_path, "wb") as f:
        shutil.copyfileobj(file.file, f)
    return {"ok": True, "filename": save_path.name}


@app.get("/templates/monthly")
def download_template():
    from .reports.monthly import find_template

    p = find_template()
    if not p:
        raise HTTPException(status_code=404, detail="No template found.")
    return FileResponse(str(p), filename=p.name)


@app.get("/templates/monthly/status")
def template_status():
    from .reports.monthly import find_template

    p = find_template()
    if p:
        return {"exists": True, "filename": p.name}
    return {"exists": False, "filename": None}


# ---------------------------------------------------------------------------
# Frontend static files — must be mounted LAST
# ---------------------------------------------------------------------------

@app.middleware("http")
async def no_cache_frontend(request, call_next):
    response = await call_next(request)
    path = request.url.path
    if path == "/" or path.endswith((".html", ".js", ".css")):
        response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    return response

_frontend_dir = Path(__file__).parent.parent / "frontend"
if _frontend_dir.exists():
    app.mount("/", StaticFiles(directory=str(_frontend_dir), html=True), name="frontend")
