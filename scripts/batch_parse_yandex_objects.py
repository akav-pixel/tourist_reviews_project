from __future__ import annotations

import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import OBJECTS_PROCESSED_CSV, REVIEWS_PROCESSED_CSV
from src.parsers.yandex_live.pipeline import run_yandex_live_pipeline


INPUT_CSV = Path("data/input/yandex_objects_50.csv")
REPORT_CSV = Path("data/processed/yandex_batch_parse_report.csv")


def clean_value(value, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value).strip()


def main() -> None:
    if not INPUT_CSV.exists():
        raise FileNotFoundError(f"Файл не найден: {INPUT_CSV}")

    objects_input = pd.read_csv(INPUT_CSV)

    required_columns = {"name", "city", "type", "url"}
    missing = required_columns - set(objects_input.columns)

    if missing:
        raise ValueError(f"В CSV не хватает колонок: {missing}")

    all_objects = []
    all_reviews = []
    report_rows = []

    total = len(objects_input)

    for index, row in objects_input.iterrows():
        name = clean_value(row.get("name"))
        city = clean_value(row.get("city"), "Өскемен")
        object_type = clean_value(row.get("type"), "attraction")
        url = clean_value(row.get("url"))

        limit = int(row.get("limit", 100)) if not pd.isna(row.get("limit", 100)) else 100
        scrolls = int(row.get("scrolls", 25)) if not pd.isna(row.get("scrolls", 25)) else 25

        print("=" * 80)
        print(f"[{index + 1}/{total}] Parsing: {name}")
        print(f"URL: {url}")

        if not url:
            print("SKIPPED: empty url")
            report_rows.append(
                {
                    "name": name,
                    "city": city,
                    "type": object_type,
                    "url": url,
                    "status": "skipped",
                    "reviews_count": 0,
                    "error": "empty url",
                }
            )
            continue

        try:
            objects_df, reviews_df = run_yandex_live_pipeline(
                url=url,
                name=name,
                city=city,
                object_type=object_type,
                limit=limit,
                headless=True,
                scrolls=scrolls,
                save_debug_html=False,
                include_sample_data=False,
            )

            reviews_count = len(reviews_df)

            all_objects.append(objects_df)
            all_reviews.append(reviews_df)

            report_rows.append(
                {
                    "name": name,
                    "city": city,
                    "type": object_type,
                    "url": url,
                    "status": "success",
                    "reviews_count": reviews_count,
                    "error": "",
                }
            )

            print(f"SUCCESS: {reviews_count} reviews")

        except Exception as exc:
            print(f"ERROR: {name}: {exc}")

            report_rows.append(
                {
                    "name": name,
                    "city": city,
                    "type": object_type,
                    "url": url,
                    "status": "error",
                    "reviews_count": 0,
                    "error": str(exc),
                }
            )

        # пауза, чтобы не перегружать браузер и сайт
        time.sleep(3)

    if all_objects:
        final_objects = pd.concat(all_objects, ignore_index=True)
        final_objects = final_objects.drop_duplicates(
            subset=["source", "source_object_id"],
            keep="last",
        )
    else:
        final_objects = pd.DataFrame()

    if all_reviews:
        final_reviews = pd.concat(all_reviews, ignore_index=True)
        final_reviews = final_reviews.drop_duplicates(
            subset=["source", "review_id"],
            keep="last",
        )
    else:
        final_reviews = pd.DataFrame()

    OBJECTS_PROCESSED_CSV.parent.mkdir(parents=True, exist_ok=True)

    final_objects.to_csv(
        OBJECTS_PROCESSED_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    final_reviews.to_csv(
        REVIEWS_PROCESSED_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    report = pd.DataFrame(report_rows)
    report.to_csv(REPORT_CSV, index=False, encoding="utf-8-sig")

    print("=" * 80)
    print("Batch parsing completed")
    print(f"Objects saved: {len(final_objects)} -> {OBJECTS_PROCESSED_CSV}")
    print(f"Reviews saved: {len(final_reviews)} -> {REVIEWS_PROCESSED_CSV}")
    print(f"Report saved: {REPORT_CSV}")


if __name__ == "__main__":
    main()