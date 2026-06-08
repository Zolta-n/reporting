import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate, Spacer

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

_ACCENT = HexColor("#2563eb")
_DARK   = HexColor("#1a1d23")
_MUTED  = HexColor("#6b7280")
_RULE   = HexColor("#dde1e7")

_H1   = ParagraphStyle("H1",   fontName="Helvetica-Bold",    fontSize=18, textColor=_ACCENT, leading=22, spaceAfter=4)
_H2   = ParagraphStyle("H2",   fontName="Helvetica-Bold",    fontSize=13, textColor=_DARK,   leading=17, spaceBefore=18, spaceAfter=5)
_H3   = ParagraphStyle("H3",   fontName="Helvetica-BoldOblique", fontSize=11, textColor=_DARK, leading=14, spaceBefore=10, spaceAfter=4)
_BODY = ParagraphStyle("Body", fontName="Helvetica",          fontSize=10, textColor=_DARK,   leading=14, spaceAfter=5)
_ITEM = ParagraphStyle("Item", fontName="Helvetica",          fontSize=10, textColor=_DARK,   leading=14, spaceAfter=4, leftIndent=14)
_NONE = ParagraphStyle("None", fontName="Helvetica-Oblique",  fontSize=10, textColor=_MUTED,  leading=14, spaceAfter=5)
_META = ParagraphStyle("Meta", fontName="Helvetica",          fontSize=8,  textColor=_MUTED,  leading=12, spaceAfter=12)


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _load_style() -> str:
    p = Path("REPORT_STYLE.md")
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _get_summary(snippets: list[str], topic: str | None = None) -> str:
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return "(summary unavailable)"
    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        combined = "\n\n".join(snippets)
        if len(combined) > 8000:
            combined = combined[:8000] + "..."
        style = _load_style()

        if topic:
            prompt = (
                f"You are writing the '{topic}' theme in an executive intermediate report.\n"
                f"Summarize the following entries about '{topic}' in 1-2 short sentences.\n"
                "Do not use bullet points. Do not mention individual person names.\n"
                "Keep customer names, company names, and figures.\n"
                "Omit email headers, greetings, and irrelevant detail.\n"
                f"\nStyle guide:\n{style}\n"
                f"\nEntries:\n{combined}"
            )
        else:
            prompt = (
                "You are writing the summary of an executive intermediate report.\n"
                "Summarize the following entries in 1-2 short sentences.\n"
                "State the overall situation, key outcomes, and any critical actions or risks.\n"
                "Do not use bullet points. Do not mention individual person names.\n"
                "Keep customer names, company names, and figures.\n"
                "Omit email headers, greetings, and irrelevant detail.\n"
                f"\nStyle guide:\n{style}\n"
                f"\nEntries:\n{combined}"
            )
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=200,
            messages=[{"role": "user", "content": prompt}],
        )
        return msg.content[0].text.strip()
    except Exception:
        return "(summary unavailable)"


def _fmt_date(dt: datetime) -> str:
    return dt.strftime("%Y-%m-%d")


def generate_intermediate_report(
    entries: list,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> Path:
    now = datetime.now(timezone.utc)

    if end_date is None:
        end_date = now
    if start_date is None:
        start_date = end_date - timedelta(days=7)

    def _naive(dt: datetime) -> datetime:
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    start_naive = _naive(start_date)
    end_naive = _naive(end_date)

    filtered = [e for e in entries if start_naive <= _naive(e.date_stamp) <= end_naive]

    year, week_num, _ = end_date.isocalendar()
    week_label = f"{year}-W{week_num:02d}"
    date_range = f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d')}"
    title = f"Intermediate Report — {week_label} ({date_range})"

    by_type: dict[str, list] = defaultdict(list)
    for e in filtered:
        by_type[e.type].append(e)

    all_snippets = [e.content[:500] for e in filtered]
    overall_summary = _get_summary(all_snippets) if all_snippets else "(no entries this period)"

    tag_groups: dict[str, list[str]] = defaultdict(list)
    for e in filtered:
        for tag in (e.tags or []):
            tag_groups[tag].append(e.content[:500])
    themes = [
        (tag, _get_summary(snips, topic=tag))
        for tag, snips in tag_groups.items()
    ]

    # ── Build PDF ──────────────────────────────────────────────────────────
    ts = now.strftime("%Y%m%dT%H%M")
    filename = f"intermediate_{week_label}_generated-{ts}.pdf"
    output_path = REPORTS_DIR / filename

    doc = SimpleDocTemplate(
        str(output_path),
        pagesize=A4,
        leftMargin=2.2 * cm,
        rightMargin=2.2 * cm,
        topMargin=2 * cm,
        bottomMargin=2 * cm,
        title=title,
        author="Reporting App",
    )

    story = []

    # Title block
    story.append(Paragraph(_esc(title), _H1))
    story.append(Paragraph(_esc(f"Generated {now.strftime('%Y-%m-%d %H:%M')} UTC"), _META))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_ACCENT, spaceAfter=10))

    # Summary
    story.append(Paragraph("Summary", _H2))
    story.append(Paragraph(_esc(overall_summary), _BODY))

    # Entries by type
    story.append(Paragraph("Entries by Type", _H2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_RULE, spaceAfter=6))

    def _add_section(heading: str, type_key: str, fmt_fn):
        items = by_type.get(type_key, [])
        if not items:
            return
        story.append(Paragraph(heading, _H3))
        for e in items:
            story.append(Paragraph(_esc(fmt_fn(e)), _ITEM))

    def _fmt_file(e):
        return f"{_fmt_date(e.date_stamp)} — {e.source}: {e.content[:200]}"

    def _fmt_email(e):
        subject = "(no subject)"
        for line in e.content.split("\n"):
            if line.startswith("Subject:"):
                subject = line[8:].strip()
                break
        return f"{_fmt_date(e.date_stamp)} — {e.source}: {subject} — {e.content[:200]}"

    def _fmt_note(e):
        return f"{_fmt_date(e.date_stamp)}: {e.content[:200]}"

    _add_section("Files",  "file",  _fmt_file)
    _add_section("Emails", "email", _fmt_email)
    _add_section("Notes",  "text",  _fmt_note)

    if not filtered:
        story.append(Paragraph("No entries for this period.", _NONE))

    # Key Themes
    story.append(Spacer(1, 6))
    story.append(Paragraph("Key Themes", _H2))
    story.append(HRFlowable(width="100%", thickness=0.5, color=_RULE, spaceAfter=6))
    if themes:
        for tag, summary_text in themes:
            story.append(Paragraph(f"<b>{_esc(tag)}:</b> {_esc(summary_text)}", _BODY))
    else:
        story.append(Paragraph("No tagged themes.", _NONE))

    doc.build(story)
    return output_path
