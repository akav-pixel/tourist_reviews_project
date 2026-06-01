from __future__ import annotations

import html
import re
from typing import Any

_TAG_RE = re.compile(r'<[^>]+>')
_SPACE_RE = re.compile(r'\s+')


def clean_text(value: Any) -> str:
    """Clean review text while preserving Russian and Kazakh characters."""
    if value is None:
        return ''
    text = str(value)
    text = html.unescape(text)
    text = _TAG_RE.sub(' ', text)
    text = text.replace('\u00a0', ' ')
    text = _SPACE_RE.sub(' ', text)
    return text.strip()


def normalize_name(value: Any) -> str:
    text = clean_text(value).lower()
    text = re.sub(r'[^0-9a-zа-яёәғқңөұүһі\s-]+', ' ', text, flags=re.IGNORECASE)
    text = _SPACE_RE.sub(' ', text).strip()
    return text
