import hashlib
import re
import string


def normalize_content(content: str) -> str:
    content = content.lower()
    content = re.sub(r"\s+", " ", content)
    content = content.translate(str.maketrans("", "", string.punctuation))
    return content.strip()


def compute_hash(content: str) -> str:
    normalized = normalize_content(content)
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()
