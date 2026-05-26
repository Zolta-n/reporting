# SPEC.md — Implementation Decisions & Open Questions

This file documents decisions made during implementation that were not fully specified in CLAUDE.md.

---

## Decisions Made

### 1. AI Model ID
**CLAUDE.md says**: `claude-haiku-4-5`  
**Implemented as**: `claude-haiku-4-5-20251001`  
The Anthropic SDK requires a versioned model ID. `claude-haiku-4-5-20251001` is the current stable Haiku 4.5 model. If Anthropic retires this version, update the `model=` parameter in `backend/reports/weekly.py` and `backend/reports/monthly.py`.

---

### 2. Default Monthly Template
**CLAUDE.md says**: "If no template is found, generation is blocked."  
**Implemented**: A minimal default `templates/monthly_report_template.md` is included in the repo so the app works out of the box. Users can replace it via the Template tab. This does not conflict with the spec — the "upload required" guard still fires if the file is absent.

---

### 3. Email Paste vs. .eml Upload Entry Type
Both result in `type = "email"`. When the user pastes raw email text in the Email tab, they can supply the sender in the "Sender (source)" field; otherwise it defaults to `"email-paste"`. The app does not auto-parse headers from pasted email — the raw pasted text becomes `content` as-is, letting users paste any format.

---

### 4. Key Themes (Weekly Report)
**CLAUDE.md says**: "one sentence per Key Theme bullet."  
**Implemented**: Themes are grouped by tag. If an entry has no tags, it contributes to the overall `## Summary` but does not appear in `## Key Themes`. The themes section shows `_No tagged themes._` when no entries have tags.

---

### 5. Date Storage (SQLite / Timezone)
SQLite does not store timezone info. All datetimes are stored as UTC naive strings (timezone stripped before insert). When read back, they are treated as UTC. The API accepts ISO 8601 strings with optional timezone offset for `date_stamp` overrides.

---

### 6. Deduplication Scope
The SHA-256 hash is computed over the **normalized** content (lowercased, whitespace collapsed, punctuation stripped). This means two files with identical text but different whitespace/capitalisation will be treated as duplicates. Phase-2 near-duplicate detection (TF-IDF cosine similarity) is out of scope per CLAUDE.md.

---

### 7. Filename Collision on Upload
If two different files share the same filename, the second upload overwrites the first in `data/uploads/`. The entry content is stored in the database (and deduplication runs), so no data is lost from the DB perspective. A production system would use UUIDs in the filename; deferred to Phase 2.

---

### 8. Monthly Report for DOCX Templates
Placeholder replacement in `.docx` files only replaces text within `run` objects. If a placeholder spans multiple runs (which Word sometimes does when typing), it will not be replaced. Workaround: type placeholders as a single unformatted run, or use `.md`/`.html` templates.

---

### 9. Static File Serving
The FastAPI `StaticFiles` mount at `/` serves `frontend/index.html` as the SPA root. API routes are registered before the mount, so `/entries`, `/reports`, etc. are not intercepted by the static handler.

---

## Open Questions

| # | Question | Decision needed |
|---|----------|-----------------|
| 1 | Should uploaded files be retained if the entry is deleted? | Currently files remain in `data/uploads/` after entry deletion. Delete cascade is not implemented. |
| 2 | Should the weekly report's date range be inclusive of the end date's full day? | Currently the end datetime defaults to `utcnow()` (mid-day). Pass an explicit `end_date` with time `23:59:59` to capture the full day. |
| 3 | Should CSV files be treated as `type=file` or have their own type? | Currently `type=file`. Add a new enum value if per-type filtering of CSVs becomes needed. |
| 4 | Near-duplicate detection (Phase 2) — threshold and action? | CLAUDE.md says cosine similarity > 0.95 warns but does not hard-reject. Not implemented. |
