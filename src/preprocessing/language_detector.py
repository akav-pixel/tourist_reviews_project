from __future__ import annotations

import re
from typing import Any

KAZAKH_SPECIFIC = set('әғқңөұүһіӘҒҚҢӨҰҮҺІ')
CYRILLIC_RE = re.compile(r'[А-Яа-яЁёӘәҒғҚқҢңӨөҰұҮүҺһІі]')
LATIN_RE = re.compile(r'[A-Za-z]')


def detect_language(value: Any) -> str:
    """Rule-based language detector for diploma prototype.

    Returns: ru, kk, mixed, unknown.
    It is intentionally simple and transparent for academic explanation.
    """
    if value is None:
        return 'unknown'
    text = str(value).strip()
    if len(text) < 3:
        return 'unknown'

    has_cyrillic = bool(CYRILLIC_RE.search(text))
    has_latin = bool(LATIN_RE.search(text))
    has_kazakh_specific = any(ch in KAZAKH_SPECIFIC for ch in text)

    if has_kazakh_specific and has_latin:
        return 'mixed'
    if has_kazakh_specific:
        return 'kk'
    if has_cyrillic and has_latin:
        return 'mixed'
    if has_cyrillic:
        return 'ru'
    return 'unknown'
