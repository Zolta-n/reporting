import json
import os
import re
from pathlib import Path

REPORTS_DIR = Path("reports")
FINALS_DIR = REPORTS_DIR / "finals"
STYLE_PATH = Path("REPORT_STYLE.md")


def extract_text(filepath: Path) -> str:
    ext = filepath.suffix.lower()
    if ext in (".md", ".html", ".txt"):
        return filepath.read_text(encoding="utf-8")
    if ext == ".docx":
        from docx import Document
        doc = Document(str(filepath))
        return "\n".join(p.text for p in doc.paragraphs if p.text.strip())
    return filepath.read_text(encoding="utf-8", errors="ignore")


def find_latest_generated(year: int, month: int) -> Path | None:
    matches = []
    for ext in (".md", ".html", ".docx"):
        matches.extend(REPORTS_DIR.glob(f"monthly_{year}-{month:02d}_generated-*{ext}"))
    if not matches:
        return None
    return max(matches, key=lambda p: p.stat().st_mtime)


def find_final(year: int, month: int) -> Path | None:
    for ext in (".md", ".html", ".docx"):
        p = FINALS_DIR / f"monthly_{year}-{month:02d}_final{ext}"
        if p.exists():
            return p
    return None


def extract_lessons(year: int, month: int) -> dict:
    generated_path = find_latest_generated(year, month)
    final_path = find_final(year, month)

    if not generated_path:
        return {"error": f"No generated report found for {year}-{month:02d}."}
    if not final_path:
        return {"error": f"No final report found for {year}-{month:02d}."}

    generated_text = extract_text(generated_path)
    final_text = extract_text(final_path)
    style = STYLE_PATH.read_text(encoding="utf-8") if STYLE_PATH.exists() else ""

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        return {"error": "ANTHROPIC_API_KEY not set — cannot extract lessons."}

    prompt = (
        "You are a writing coach reviewing how an AI-generated executive monthly report "
        "was edited by a human before distribution.\n\n"
        f"Current style guide:\n{style}\n\n"
        f"AI-generated version:\n{generated_text[:3000]}\n\n"
        f"Final edited version:\n{final_text[:3000]}\n\n"
        "Identify 3 to 6 concrete, actionable lessons about style, categorization, tone, or "
        "structure that should be added to the style guide to reduce the amount of editing "
        "needed in the future.\n"
        "Each lesson should be a short, specific rule (1-2 sentences).\n"
        "Return ONLY a JSON array of strings, no explanation.\n"
        'Example: ["Do not mention email subjects in the report body.", '
        '"Merge related project updates into a single paragraph."]'
    )

    try:
        import anthropic
        client = anthropic.Anthropic(api_key=api_key)
        msg = client.messages.create(
            model="claude-haiku-4-5-20251001",
            max_tokens=1000,
            messages=[
                {"role": "user", "content": prompt},
                {"role": "assistant", "content": "["},
            ],
        )
        # Prepend the prefilled "[" that was used to steer the response
        text = "[" + msg.content[0].text.strip()
        # Strip markdown code fences if somehow still present
        text = re.sub(r"^```[a-z]*\n?", "", text)
        text = re.sub(r"\n?```$", "", text)
        text = text.strip()

        # Try direct parse first; if that fails, extract the first [...] array found
        try:
            lessons = json.loads(text)
        except json.JSONDecodeError:
            m = re.search(r"\[.*?\]", text, re.DOTALL)
            if not m:
                return {"error": "AI response did not contain a JSON array. Try again."}
            lessons = json.loads(m.group(0))

        if not isinstance(lessons, list):
            lessons = [str(lessons)]
        return {
            "lessons": [str(l) for l in lessons if str(l).strip()],
            "generated": generated_path.name,
            "final": final_path.name,
        }
    except Exception as exc:
        return {"error": str(exc)}
