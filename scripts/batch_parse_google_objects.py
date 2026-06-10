from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
SCRIPT_DIR = Path(__file__).resolve().parent

if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

if str(SCRIPT_DIR) not in sys.path:
    sys.path.insert(0, str(SCRIPT_DIR))

from parse_google_one import (  # noqa: E402
    GoogleConfig,
    parse_google_reviews,
    save_raw_result,
    append_to_processed,
)


DEFAULT_INPUT_CSV = Path("data/input/google_objects.csv")
DEFAULT_REPORT_CSV = Path("data/processed/google_batch_parse_report.csv")


def clean_value(value, default: str = "") -> str:
    if pd.isna(value):
        return default
    return str(value).strip()


def read_input_csv(path: Path) -> pd.DataFrame:
    df = pd.read_csv(path, encoding="utf-8-sig")

    df.columns = (
        df.columns
        .astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    df = df.map(lambda value: value.strip() if isinstance(value, str) else value)

    required = {"name", "city", "type", "url"}
    missing = required - set(df.columns)

    if missing:
        raise ValueError(f"В CSV не хватает колонок: {missing}")

    return df


def main() -> None:
    parser = argparse.ArgumentParser(description="Batch Google Maps parser")
    parser.add_argument("--input", default=str(DEFAULT_INPUT_CSV))
    parser.add_argument("--report", default=str(DEFAULT_REPORT_CSV))
    parser.add_argument("--visible", action="store_true")
    parser.add_argument("--pause", type=float, default=5.0)

    args = parser.parse_args()

    input_csv = Path(args.input)
    report_csv = Path(args.report)

    if not input_csv.exists():
        raise FileNotFoundError(f"CSV файл не найден: {input_csv}")

    objects = read_input_csv(input_csv)

    report_rows = []
    total = len(objects)

    for index, row in objects.iterrows():
        name = clean_value(row.get("name"))
        city = clean_value(row.get("city"), "Өскемен")
        object_type = clean_value(row.get("type"), "cultural_object")
        url = clean_value(row.get("url"))

        limit = int(row.get("limit", 50)) if not pd.isna(row.get("limit", 50)) else 50
        scrolls = int(row.get("scrolls", 50)) if not pd.isna(row.get("scrolls", 50)) else 50

        print("=" * 90)
        print(f"[{index + 1}/{total}] Google Maps parsing: {name}")
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
            config = GoogleConfig(
                url=url,
                name=name,
                city=city,
                object_type=object_type,
                limit=limit,
                scrolls=scrolls,
                headless=not args.visible,
            )

            result = parse_google_reviews(config)
            json_path, csv_path = save_raw_result(result)

            reviews_count = len(result.get("reviews", []))

            print(f"Raw JSON saved: {json_path}")
            print(f"Raw CSV saved: {csv_path}")
            print(f"Parsed reviews: {reviews_count}")

            append_to_processed(result)

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

        time.sleep(args.pause)

    report_csv.parent.mkdir(parents=True, exist_ok=True)

    report = pd.DataFrame(report_rows)
    report.to_csv(report_csv, index=False, encoding="utf-8-sig")

    print("=" * 90)
    print("Google batch parsing completed")
    print(f"Report saved: {report_csv}")


if __name__ == "__main__":
    main()