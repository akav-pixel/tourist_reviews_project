from __future__ import annotations

import re
from urllib.parse import parse_qs, unquote, urlparse


_OID_PATTERNS = [
    re.compile(r"/org/[^/]+/(?P<oid>\d{6,})"),
    re.compile(r"/maps/org/[^/]+/(?P<oid>\d{6,})"),
    re.compile(r"[?&]oid=(?P<oid>\d{6,})"),
    re.compile(r"[?&]orgpage%5Bid%5D=(?P<oid>\d{6,})"),
    re.compile(r"[?&]orgpage\[id\]=(?P<oid>\d{6,})"),
]


def extract_yandex_oid(url: str) -> str:
    """Extract Yandex organization id from common Yandex Maps URL formats."""
    if not url or not isinstance(url, str):
        raise ValueError("Yandex URL is empty")

    raw = url.strip()
    decoded = unquote(raw)

    for candidate in (raw, decoded):
        for pattern in _OID_PATTERNS:
            match = pattern.search(candidate)
            if match:
                return match.group("oid")

    parsed = urlparse(raw)
    query = parse_qs(parsed.query)
    for key in ("oid", "orgpage[id]", "orgpage%5Bid%5D"):
        values = query.get(key)
        if values and values[0].isdigit():
            return values[0]

    # Last-resort fallback: the longest numeric segment in URL.
    numbers = re.findall(r"\d{6,}", decoded)
    if numbers:
        return max(numbers, key=len)

    raise ValueError(f"Cannot extract Yandex organization id from URL: {url}")


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(description="Extract Yandex organization id from URL")
    parser.add_argument("url")
    args = parser.parse_args()
    print(extract_yandex_oid(args.url))
