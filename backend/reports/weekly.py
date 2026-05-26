import os
from collections import defaultdict
from datetime import datetime, timedelta, timezone
from pathlib import Path

REPORTS_DIR = Path("reports")
REPORTS_DIR.mkdir(exist_ok=True)


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
                f"You are writing the '{topic}' theme in an executive weekly report.\n"
                f"Summarize the following entries about '{topic}' in 1-2 short sentences.\n"
                "Do not use bullet points. Do not mention individual person names.\n"
                "Keep customer names, company names, and figures.\n"
                "Omit email headers, greetings, and irrelevant detail.\n"
                f"\nStyle guide:\n{style}\n"
                f"\nEntries:\n{combined}"
            )
        else:
            prompt = (
                "You are writing the summary of an executive weekly report.\n"
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


def generate_weekly_report(
    entries: list,
    start_date: datetime | None = None,
    end_date: datetime | None = None,
) -> Path:
    now = datetime.now(timezone.utc)

    if end_date is None:
        end_date = now
    if start_date is None:
        start_date = end_date - timedelta(days=7)

    # Normalise to naive UTC for comparison with SQLite-stored datetimes
    def _naive(dt: datetime) -> datetime:
        return dt.replace(tzinfo=None) if dt.tzinfo else dt

    start_naive = _naive(start_date)
    end_naive = _naive(end_date)

    filtered = [
        e for e in entries
        if start_naive <= _naive(e.date_stamp) <= end_naive
    ]

    year, week_num, _ = end_date.isocalendar()
    week_label = f"{year}-W{week_num:02d}"
    date_range = f"{start_date.strftime('%b %d')} – {end_date.strftime('%b %d')}"

    by_type: dict[str, list] = defaultdict(list)
    for e in filtered:
        by_type[e.type].append(e)

    all_snippets = [e.content[:500] for e in filtered]

    # Build per-type sections
    def _files_section() -> str:
        items = by_type.get("file", [])
        if not items:
            return ""
        lines = [
            f"- {_fmt_date(e.date_stamp)} — {e.source}: {e.content[:200]}"
            for e in items
        ]
        return "### Files\n" + "\n".join(lines)

    def _emails_section() -> str:
        items = by_type.get("email", [])
        if not items:
            return ""
        lines = []
        for e in items:
            subject = "(no subject)"
            for line in e.content.split("\n"):
                if line.startswith("Subject:"):
                    subject = line[8:].strip()
                    break
            lines.append(
                f"- {_fmt_date(e.date_stamp)} — {e.source}: {subject} — {e.content[:200]}"
            )
        return "### Emails\n" + "\n".join(lines)

    def _notes_section() -> str:
        items = by_type.get("text", [])
        if not items:
            return ""
        lines = [f"- {_fmt_date(e.date_stamp)}: {e.content[:200]}" for e in items]
        return "### Notes\n" + "\n".join(lines)

    parts = [s for s in [_files_section(), _emails_section(), _notes_section()] if s]
    entries_block = "\n\n".join(parts) if parts else "_No entries for this period._"

    overall_summary = _get_summary(all_snippets) if all_snippets else "(no entries this period)"

    # Key themes by tag
    tag_groups: dict[str, list[str]] = defaultdict(list)
    for e in filtered:
        for tag in (e.tags or []):
            tag_groups[tag].append(e.content[:500])

    theme_lines = [
        f"- **{tag}**: {_get_summary(snips, topic=tag)}"
        for tag, snips in tag_groups.items()
    ]
    themes_block = "\n".join(theme_lines) if theme_lines else "_No tagged themes._"

    report = f"""# Weekly Report — {week_label} ({date_range})

## Summary
{overall_summary}

## Entries by Type

{entries_block}

## Key Themes
{themes_block}
"""

    ts = now.strftime("%Y%m%dT%H%M")
    filename = f"weekly_{week_label}_generated-{ts}.md"
    output_path = REPORTS_DIR / filename
    output_path.write_text(report, encoding="utf-8")
    return output_path
