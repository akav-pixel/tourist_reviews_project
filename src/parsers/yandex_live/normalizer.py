from __future__ import annotations

from pathlib import Path

import pandas as pd

from .extract_oid import extract_yandex_oid


REVIEW_COLUMNS = [
    "source",
    "review_id",
    "source_object_id",
    "author",
    "review_text",
    "rating",
    "review_date",
    "url",
]


def normalize_yandex_reviews(
    input_path: str | Path,
    output_path: str | Path,
    source_object_id: str | None = None,
    source_url: str | None = None,
) -> pd.DataFrame:
    """Normalize raw Yandex reviews CSV/JSON to the common project review schema."""
    input_path = Path(input_path)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if input_path.suffix.lower() == ".json":
        df = pd.read_json(input_path)
    else:
        df = pd.read_csv(input_path)

    result = pd.DataFrame()
    result["source"] = "yandex"

    if "review_id" in df.columns:
        result["review_id"] = df["review_id"].astype(str)
    elif "id" in df.columns:
        result["review_id"] = df["id"].astype(str)
    else:
        result["review_id"] = [f"yandex_{i + 1:06d}" for i in range(len(df))]

    if source_object_id:
        result["source_object_id"] = source_object_id
    elif "source_object_id" in df.columns:
        result["source_object_id"] = df["source_object_id"].astype(str)
    elif "object_id" in df.columns:
        result["source_object_id"] = df["object_id"].astype(str)
    elif source_url:
        result["source_object_id"] = extract_yandex_oid(source_url)
    else:
        result["source_object_id"] = "yandex_unknown_object"

    result["author"] = df.get("author", df.get("user", "")).fillna("").astype(str)
    result["review_text"] = df.get("review_text", df.get("text", df.get("comment", ""))).fillna("").astype(str)

    rating = df.get("rating", df.get("stars", None))
    result["rating"] = pd.to_numeric(rating, errors="coerce") if rating is not None else None

    review_date = df.get("review_date", df.get("date", None))
    result["review_date"] = pd.to_datetime(review_date, errors="coerce").dt.date if review_date is not None else None

    if "url" in df.columns:
        result["url"] = df["url"].fillna(source_url or "").astype(str)
    else:
        result["url"] = source_url or ""

    result = result[REVIEW_COLUMNS]
    result.to_csv(output_path, index=False, encoding="utf-8-sig")
    return result
