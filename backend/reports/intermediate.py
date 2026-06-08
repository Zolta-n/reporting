import json
import os
import re
from datetime import datetime, timedelta, timezone
from pathlib import Path

from reportlab.lib.colors import HexColor
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import cm
from reportlab.platypus import HRFlowable, Paragraph, SimpleDocTemplate

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)

_ACCENT = HexColor("#2563eb")
_DARK   = HexColor("#1a1d23")
_MUTED  = HexColor("#6b7280")

_H1     = ParagraphStyle("H1",     fontName="Helvetica-Bold",   fontSize=18, textColor=_ACCENT, leading=22, spaceAfter=4)
_META   = ParagraphStyle("Meta",   fontName="Helvetica",        fontSize=8,  textColor=_MUTED,  leading=12, spaceAfter=12)
_BULLET = ParagraphStyle("Bullet", fontName="Helvetica",        fontSize=10.5, textColor=_DARK, leading=16, spaceAfter=10, leftIndent=16, firstLineIndent=-16)
_NONE   = ParagraphStyle("None",   fontName="Helvetica-Oblique",fontSize=10, textColor=_MUTED,  leading=14, spaceAfter=5)


def _esc(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def _load_style() -> str:
    p = Path("REPORT_STYLE.md")
    return p.read_text(encoding="utf-8") if p.exists() else ""


def _get_bullet_points(entries: list) -> list[str]:
    """Single AI call: group by topic, deduplicate, condense each to 1-2 sentences."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")

    if not api_key:
        seen: set[str] = set()
        result = []
        for e in entries:
            text = e.content[:200].strip()
            if text and text not in seen:
                seen.add(text)
                result.append(text)
        return result

    style = _load_style()
    raw = "\n\n".join(
        f"[{e.type}] {e.source}:\n{e.content[:500]}"
        for e in entries
    )

    prompt = (
        "You are generating an executive intermediate business report as a flat bullet list.\n\n"
        "Instructions:\n"
        "- Identify all distinct business topics across the entries below\n"
        "- Group entries that refer to the same topic\n"
        "- For each topic, write exactly 1-2 sentences capturing the essential business information\n"
        "- Each topic must appear EXACTLY ONCE — never repeat the same topic\n"
        "- No section headings, no sub-categories, no person names\n"
        "- Keep company names, customer names, product names, and figures\n"
        "- Condense lengthy entries to their core business relevance\n"
        "- Omit email headers, greetings, signatures, and procedural detail\n"
        f"\nStyle guide:\n{style}\n\n"
        "Return ONLY a JSON array of strings. Each string is one topic (1-2 sentences).\n"
        "Example:\n"
        '["NIO project nomination confirmed with nomination letter received; monthly demand is 32K sets.", '
        '"Forvia forecast reduced significantly with unclear reasoning; a purchasing visit is scheduled to clarify."]\n\n'
        f"Entries:\n{raw}"
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1500,
            messages=[{"role": "user", "content": prompt}],
        )
        text = msg.content[0].text.strip()
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()
        data = json.loads(text)
        if isinstance(data, list):
            return [s.strip() for s in data if isinstance(s, str) and s.strip()]
        return []
    except Exception:
        return [e.content[:200].strip() for e in entries[:20]]


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

    filtered = [
        e for e in entries
        if _naive(start_date) <= _naive(e.date_stamp) <= _naive(end_date)
    ]

    year, week_num, _ = end_date.isocalendar()
    week_label = f"{year}-W{week_num:02d}"
    date_range = f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d')}"
    title = f"Intermediate Report — {week_label} ({date_range})"

    bullet_points = _get_bullet_points(filtered) if filtered else []

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
    story.append(Paragraph(_esc(title), _H1))
    story.append(Paragraph(_esc(f"Generated {now.strftime('%Y-%m-%d %H:%M')} UTC"), _META))
    story.append(HRFlowable(width="100%", thickness=1.5, color=_ACCENT, spaceAfter=14))

    if bullet_points:
        for point in bullet_points:
            story.append(Paragraph(f"• {_esc(point)}", _BULLET))
    else:
        story.append(Paragraph("No entries for this period.", _NONE))

    doc.build(story)
    return output_path
