import base64
import email as email_lib
import html as html_lib
import os
import re
from pathlib import Path


ALLOWED_SUFFIXES = {".txt", ".pdf", ".docx", ".eml", ".csv", ".md",
                    ".png", ".jpg", ".jpeg", ".webp", ".gif"}

_IMAGE_SUFFIXES = {".png", ".jpg", ".jpeg", ".webp", ".gif"}
_IMAGE_MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def extract_text_from_file(file_path: Path, filename: str) -> tuple[str, str]:
    """Return (content, source) from a saved upload file."""
    suffix = Path(filename).suffix.lower()

    if suffix in (".txt", ".md"):
        return file_path.read_text(encoding="utf-8", errors="replace"), filename

    if suffix == ".pdf":
        import pdfplumber

        parts: list[str] = []
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if text:
                    parts.append(text)
        return "\n".join(parts), filename

    if suffix == ".docx":
        from docx import Document

        doc = Document(str(file_path))
        return "\n".join(p.text for p in doc.paragraphs if p.text), filename

    if suffix == ".eml":
        return parse_eml_file(file_path), filename

    if suffix == ".csv":
        import csv

        rows: list[str] = []
        with open(file_path, newline="", encoding="utf-8", errors="replace") as f:
            for row in csv.reader(f):
                rows.append(", ".join(row))
        return "\n".join(rows), filename

    if suffix in _IMAGE_SUFFIXES:
        return extract_text_from_image(file_path, suffix), filename

    # Fallback: read as text
    return file_path.read_text(encoding="utf-8", errors="replace"), filename


def extract_text_from_image(file_path: Path, suffix: str) -> str:
    """Use Claude vision to extract text and content from a screenshot or image."""
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise ValueError(
            "ANTHROPIC_API_KEY is required to process screenshots. "
            "Please set it in your .env file."
        )

    import anthropic

    media_type = _IMAGE_MEDIA_TYPES.get(suffix, "image/png")
    image_data = base64.standard_b64encode(file_path.read_bytes()).decode("utf-8")

    client = anthropic.Anthropic(api_key=api_key)
    msg = client.messages.create(
        model="claude-haiku-4-5-20251001",
        max_tokens=2000,
        messages=[{
            "role": "user",
            "content": [
                {
                    "type": "image",
                    "source": {
                        "type": "base64",
                        "media_type": media_type,
                        "data": image_data,
                    },
                },
                {
                    "type": "text",
                    "text": (
                        "Extract all meaningful text and information from this screenshot. "
                        "Preserve structure: keep tables as rows, lists as lines, headings intact. "
                        "Return only the extracted content — no commentary, no preamble."
                    ),
                },
            ],
        }],
    )
    return msg.content[0].text.strip()


def parse_eml_file(file_path: Path) -> str:
    """Parse an .eml file and return structured text content."""
    msg = email_lib.message_from_bytes(file_path.read_bytes())
    subject = msg.get("Subject", "(no subject)")
    sender = msg.get("From", "(unknown sender)")
    date = msg.get("Date", "")
    body = _extract_body(msg)
    return f"From: {sender}\nDate: {date}\nSubject: {subject}\n\n{body}"


def parse_email_paste(raw: str) -> dict[str, str]:
    """Parse a pasted raw email string into structured fields."""
    msg = email_lib.message_from_string(raw)
    return {
        "subject": msg.get("Subject", "(no subject)"),
        "sender": msg.get("From", "(unknown sender)"),
        "date": msg.get("Date", ""),
        "body": _extract_body(msg),
    }


def _extract_body(msg) -> str:
    if msg.is_multipart():
        for part in msg.walk():
            if part.get_content_type() == "text/plain":
                payload = part.get_payload(decode=True)
                if payload:
                    return payload.decode("utf-8", errors="replace")
        for part in msg.walk():
            if part.get_content_type() == "text/html":
                payload = part.get_payload(decode=True)
                if payload:
                    text = payload.decode("utf-8", errors="replace")
                    text = re.sub(r"<[^>]+>", " ", text)
                    return html_lib.unescape(text)
        return ""

    payload = msg.get_payload(decode=True)
    if payload:
        return payload.decode("utf-8", errors="replace")
    return str(msg.get_payload() or "")
