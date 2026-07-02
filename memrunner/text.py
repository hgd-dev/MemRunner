from __future__ import annotations

import re
import unicodedata


def clean_text(value: str | None) -> str:
    text = unicodedata.normalize("NFKC", value or "")
    text = re.sub(r"\s+", " ", text)
    return text.strip()


def strip_choice_prefix(value: str | None) -> str:
    text = clean_text(value)
    text = re.sub(r"^\d+\s*", "", text)
    return clean_text(text)


def normalize_key(value: str | None) -> str:
    return clean_text(value).casefold()
