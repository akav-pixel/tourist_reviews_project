from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.config import (
    OBJECTS_PROCESSED_CSV,
    REVIEWS_PROCESSED_CSV,
    SAMPLE_OBJECTS_CSV,
    SAMPLE_REVIEWS_CSV,
)
from src.importers.csv_importer import load_objects_csv, load_reviews_csv
from src.preprocessing.pipeline import preprocess_objects, preprocess_reviews
from src.reconciliation.object_matcher import add_canonical_key

from .yandex_live_parser import (
    YandexParserConfig,
    parse_yandex_reviews,
    save_raw_result,
)


CITY_ALIASES = {
    "Усть-Каменогорск": "Өскемен",
    "Усть Каменогорск": "Өскемен",
    "Каменогорск": "Өскемен",
    "Оскемен": "Өскемен",
    "Oskemen": "Өскемен",
    "Ust-Kamenogorsk": "Өскемен",
    "Ust Kamenogorsk": "Өскемен",
}


def normalize_city(value: object) -> str:
    city = str(value or "").strip()
    return CITY_ALIASES.get(city, city)


def save_raw_csv(result: dict, raw_dir: str | Path) -> Path:
    """
    Сохраняет raw-результат Яндекс-парсера в CSV.
    JSON сохраняется отдельно через save_raw_result().
    """
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    source_object_id = str(result["meta"]["source_object_id"])
    path = raw_dir / f"yandex_{source_object_id}_reviews.csv"

    reviews = result.get("reviews", [])
    df = pd.DataFrame(reviews)

    if not df.empty:
        df["source"] = "yandex"
        df["source_object_id"] = source_object_id
        df["url"] = result["meta"]["source_url"]

    df.to_csv(path, index=False, encoding="utf-8-sig")
    return path


def build_yandex_object_row(
    *,
    name: str,
    city: str,
    object_type: str,
    source_object_id: str,
    source_url: str,
) -> pd.DataFrame:
    """
    Создаёт строку объекта для tourist_objects.
    """
    return pd.DataFrame(
        [
            {
                "source": "yandex",
                "source_object_id": str(source_object_id),
                "name": name,
                "type": object_type,
                "city": normalize_city(city),
                "source_url": source_url,
                "latitude": None,
                "longitude": None,
            }
        ]
    )


def normalize_yandex_reviews_df(result: dict) -> pd.DataFrame:
    """
    Преобразует список отзывов из raw JSON в DataFrame и гарантирует,
    что каждая строка имеет правильные source/source_object_id/url.
    """
    reviews = result.get("reviews", [])
    source_object_id = str(result["meta"]["source_object_id"])
    source_url = result["meta"]["source_url"]

    df = pd.DataFrame(reviews)

    if df.empty:
        return pd.DataFrame(
            columns=[
                "source",
                "source_object_id",
                "review_id",
                "author",
                "review_text",
                "rating",
                "review_date",
                "url",
            ]
        )

    required_columns = {
        "source": "yandex",
        "source_object_id": source_object_id,
        "review_id": None,
        "author": "anonymous",
        "review_text": "",
        "rating": None,
        "review_date": None,
        "url": source_url,
    }

    for column, default in required_columns.items():
        if column not in df.columns:
            df[column] = default

    df["source"] = "yandex"
    df["source_object_id"] = source_object_id
    df["url"] = source_url

    df["review_text"] = df["review_text"].fillna("").astype(str).str.strip()
    df["review_id"] = df["review_id"].astype(str)
    df["source_object_id"] = df["source_object_id"].astype(str)

    df = df[df["review_text"] != ""].copy()
    df = df.dropna(subset=["review_id"])
    df = df.drop_duplicates(subset=["source", "review_id"], keep="last")

    return df


def load_base_objects() -> pd.DataFrame:
    """
    Загружает демонстрационные объекты, если нужно объединять
    Яндекс-данные с sample-данными.
    """
    if Path(SAMPLE_OBJECTS_CSV).exists():
        df = load_objects_csv(SAMPLE_OBJECTS_CSV)

        if "city" in df.columns:
            df["city"] = df["city"].apply(normalize_city)

        return df

    return pd.DataFrame()


def load_base_reviews() -> pd.DataFrame:
    """
    Загружает демонстрационные отзывы, если нужно объединять
    Яндекс-данные с sample-данными.
    """
    if Path(SAMPLE_REVIEWS_CSV).exists():
        return load_reviews_csv(SAMPLE_REVIEWS_CSV)

    return pd.DataFrame()


def run_yandex_live_pipeline(
    *,
    url: str,
    name: str,
    city: str,
    object_type: str,
    limit: int = 100,
    headless: bool = True,
    scrolls: int = 25,
    save_debug_html: bool = False,
    include_sample_data: bool = False,
) -> tuple[pd.DataFrame, pd.DataFrame]:
    """
    Полный ingestion pipeline для Яндекс Карт.

    Этапы:
    1. Selenium-парсер собирает raw-отзывы.
    2. Raw сохраняется в data/raw/yandex в JSON и CSV.
    3. Создаётся объект tourist_objects для Яндекс-объекта.
    4. Отзывы нормализуются.
    5. Выполняется preprocessing объектов и отзывов.
    6. Сохраняются objects_processed.csv и reviews_processed.csv.

    По умолчанию include_sample_data=False:
    это значит, что после запуска parse-yandex в processed CSV
    попадут только реальные данные Яндекс-парсера.
    Так не будет старых skipped-записей из demo-данных.
    """
    city = normalize_city(city)

    config = YandexParserConfig(
        url=url,
        city=city,
        object_type=object_type,
        limit=limit,
        headless=headless,
        scrolls=scrolls,
        save_debug_html=save_debug_html,
    )

    result = parse_yandex_reviews(config)

    raw_json_path = save_raw_result(result, config.raw_dir)
    raw_csv_path = save_raw_csv(result, config.raw_dir)

    print(f"Raw Yandex reviews saved: {raw_json_path}")
    print(f"Raw Yandex reviews CSV saved: {raw_csv_path}")
    print(f"Parsed reviews: {len(result.get('reviews', []))}")

    source_object_id = str(result["meta"]["source_object_id"])

    yandex_object = build_yandex_object_row(
        name=name,
        city=city,
        object_type=object_type,
        source_object_id=source_object_id,
        source_url=url,
    )

    yandex_reviews = normalize_yandex_reviews_df(result)

    if include_sample_data:
        base_objects = load_base_objects()
        base_reviews = load_base_reviews()

        objects_all = pd.concat(
            [base_objects, yandex_object],
            ignore_index=True,
        )

        reviews_all = pd.concat(
            [base_reviews, yandex_reviews],
            ignore_index=True,
        )
    else:
        objects_all = yandex_object.copy()
        reviews_all = yandex_reviews.copy()

    if "city" in objects_all.columns:
        objects_all["city"] = objects_all["city"].apply(normalize_city)

    objects_all["source"] = objects_all["source"].astype(str)
    objects_all["source_object_id"] = objects_all["source_object_id"].astype(str)

    reviews_all["source"] = reviews_all["source"].astype(str)
    reviews_all["source_object_id"] = reviews_all["source_object_id"].astype(str)

    objects_all = objects_all.drop_duplicates(
        subset=["source", "source_object_id"],
        keep="last",
    )

    reviews_all = reviews_all.drop_duplicates(
        subset=["source", "review_id"],
        keep="last",
    )

    objects_processed = add_canonical_key(preprocess_objects(objects_all))
    reviews_processed = preprocess_reviews(reviews_all)

    # После preprocess_objects ещё раз фиксируем город.
    if "city" in objects_processed.columns:
        objects_processed["city"] = objects_processed["city"].apply(normalize_city)

    # ВАЖНО:
    # После preprocess_reviews гарантируем, что реальные отзывы Яндекса
    # не потеряли source/source_object_id/url.
    yandex_mask = reviews_processed["review_id"].astype(str).str.startswith(
        f"yandex_{source_object_id}_"
    )

    reviews_processed.loc[yandex_mask, "source"] = "yandex"
    reviews_processed.loc[yandex_mask, "source_object_id"] = source_object_id
    reviews_processed.loc[yandex_mask, "url"] = url

    object_mask = (
        (objects_processed["source"].astype(str) == "yandex")
        & (objects_processed["source_object_id"].astype(str) == source_object_id)
    )

    objects_processed.loc[object_mask, "name"] = name
    objects_processed.loc[object_mask, "type"] = object_type
    objects_processed.loc[object_mask, "city"] = city
    objects_processed.loc[object_mask, "source_url"] = url

    objects_processed.to_csv(
        OBJECTS_PROCESSED_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    reviews_processed.to_csv(
        REVIEWS_PROCESSED_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    return objects_processed, reviews_processed