from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import quote_plus

import pandas as pd
from dotenv import load_dotenv
from sqlalchemy import create_engine, text


ROOT = Path(__file__).resolve().parents[2]
PROCESSED_DIR = ROOT / "data" / "processed"

OBJECTS_CSV = PROCESSED_DIR / "objects_processed.csv"
REVIEWS_CSV = PROCESSED_DIR / "reviews_processed.csv"
SENTIMENT_CSV = PROCESSED_DIR / "sentiment_predictions.csv"


def get_engine():
    load_dotenv()

    host = os.getenv("POSTGRES_HOST")
    port = os.getenv("POSTGRES_PORT", "6543")
    db = os.getenv("POSTGRES_DB", "postgres")
    user = os.getenv("POSTGRES_USER")
    password = os.getenv("POSTGRES_PASSWORD")
    sslmode = os.getenv("POSTGRES_SSLMODE", "require")

    if not all([host, port, db, user, password]):
        raise RuntimeError("PostgreSQL connection variables are missing in .env")

    url = (
        f"postgresql+psycopg2://{user}:{quote_plus(password)}"
        f"@{host}:{port}/{db}?sslmode={sslmode}"
    )
    return create_engine(url, pool_pre_ping=True)


def prepare_database(conn) -> None:
    """
    Создаёт индексы для защиты от дублей.
    """
    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_tourist_objects_source_object
        ON tourist_objects (source, source_object_id);
    """))

    conn.execute(text("""
        CREATE UNIQUE INDEX IF NOT EXISTS ux_reviews_source_review
        ON reviews (source, review_id);
    """))

    conn.execute(text("""
        CREATE INDEX IF NOT EXISTS ix_review_analysis_review_id
        ON review_analysis (review_id);
    """))


def load_objects(conn, objects: pd.DataFrame) -> dict[tuple[str, str], int]:
    """
    Загружает tourist_objects и возвращает mapping:
    (source, source_object_id) -> id
    """
    objects = objects.copy()

    required_defaults = {
        "source": "unknown",
        "source_object_id": None,
        "name": "unknown",
        "type": "unknown",
        "city": "unknown",
        "source_url": None,
        "latitude": None,
        "longitude": None,
    }

    for col, default in required_defaults.items():
        if col not in objects.columns:
            objects[col] = default

    objects = objects.dropna(subset=["source_object_id"])
    objects = objects.drop_duplicates(subset=["source", "source_object_id"])

    sql = text("""
        INSERT INTO tourist_objects (
            name,
            type,
            city,
            source,
            source_object_id,
            source_url,
            latitude,
            longitude
        )
        VALUES (
            :name,
            :type,
            :city,
            :source,
            :source_object_id,
            :source_url,
            :latitude,
            :longitude
        )
        ON CONFLICT (source, source_object_id)
        DO UPDATE SET
            name = EXCLUDED.name,
            type = EXCLUDED.type,
            city = EXCLUDED.city,
            source_url = EXCLUDED.source_url,
            latitude = EXCLUDED.latitude,
            longitude = EXCLUDED.longitude
        RETURNING id;
    """)

    for _, row in objects.iterrows():
        conn.execute(sql, {
            "name": row.get("name"),
            "type": row.get("type"),
            "city": row.get("city"),
            "source": row.get("source"),
            "source_object_id": str(row.get("source_object_id")),
            "source_url": row.get("source_url"),
            "latitude": None if pd.isna(row.get("latitude")) else row.get("latitude"),
            "longitude": None if pd.isna(row.get("longitude")) else row.get("longitude"),
        })

    result = conn.execute(text("""
        SELECT id, source, source_object_id
        FROM tourist_objects;
    """))

    mapping: dict[tuple[str, str], int] = {}
    for row in result:
        mapping[(str(row.source), str(row.source_object_id))] = int(row.id)

    return mapping


def load_reviews(
    conn,
    reviews: pd.DataFrame,
    object_map: dict[tuple[str, str], int],
) -> dict[str, int]:
    """
    Загружает reviews и возвращает mapping:
    review_id -> reviews.id
    """
    reviews = reviews.copy()

    required_defaults = {
        "source": "unknown",
        "source_object_id": None,
        "review_id": None,
        "author": None,
        "review_text": None,
        "text_cleaned": None,
        "rating": None,
        "rating_normalized": None,
        "review_date": None,
        "language": "unknown",
        "url": None,
        "quality_status": "valid",
        "is_duplicate": False,
    }

    for col, default in required_defaults.items():
        if col not in reviews.columns:
            reviews[col] = default

    reviews = reviews.dropna(subset=["review_id", "source_object_id"])
    reviews = reviews.drop_duplicates(subset=["source", "review_id"])

    sql = text("""
        INSERT INTO reviews (
            object_id,
            source,
            source_object_id,
            review_id,
            author,
            review_text,
            text_cleaned,
            rating,
            rating_normalized,
            review_date,
            language,
            url,
            quality_status,
            is_duplicate
        )
        VALUES (
            :object_id,
            :source,
            :source_object_id,
            :review_id,
            :author,
            :review_text,
            :text_cleaned,
            :rating,
            :rating_normalized,
            :review_date,
            :language,
            :url,
            :quality_status,
            :is_duplicate
        )
        ON CONFLICT (source, review_id)
        DO UPDATE SET
            object_id = EXCLUDED.object_id,
            source_object_id = EXCLUDED.source_object_id,
            author = EXCLUDED.author,
            review_text = EXCLUDED.review_text,
            text_cleaned = EXCLUDED.text_cleaned,
            rating = EXCLUDED.rating,
            rating_normalized = EXCLUDED.rating_normalized,
            review_date = EXCLUDED.review_date,
            language = EXCLUDED.language,
            url = EXCLUDED.url,
            quality_status = EXCLUDED.quality_status,
            is_duplicate = EXCLUDED.is_duplicate
        RETURNING id;
    """)

    inserted = 0
    skipped = 0

    for _, row in reviews.iterrows():
        key = (str(row.get("source")), str(row.get("source_object_id")))
        object_id = object_map.get(key)

        if object_id is None:
            skipped += 1
            continue

        review_date = row.get("review_date")
        if pd.isna(review_date) or str(review_date).strip() == "":
            review_date = None

        conn.execute(sql, {
            "object_id": object_id,
            "source": row.get("source"),
            "source_object_id": str(row.get("source_object_id")),
            "review_id": str(row.get("review_id")),
            "author": row.get("author"),
            "review_text": row.get("review_text"),
            "text_cleaned": row.get("text_cleaned"),
            "rating": None if pd.isna(row.get("rating")) else row.get("rating"),
            "rating_normalized": None if pd.isna(row.get("rating_normalized")) else row.get("rating_normalized"),
            "review_date": review_date,
            "language": row.get("language"),
            "url": row.get("url"),
            "quality_status": row.get("quality_status"),
            "is_duplicate": bool(row.get("is_duplicate")) if not pd.isna(row.get("is_duplicate")) else False,
        })

        inserted += 1

    result = conn.execute(text("""
        SELECT id, review_id
        FROM reviews;
    """))

    mapping: dict[str, int] = {}
    for row in result:
        mapping[str(row.review_id)] = int(row.id)

    print(f"Reviews loaded/updated: {inserted}")
    print(f"Reviews skipped because object was not found: {skipped}")

    return mapping


def load_review_analysis(
    conn,
    predictions: pd.DataFrame,
    review_map: dict[str, int],
) -> None:
    """
    Загружает sentiment_predictions.csv в review_analysis.
    """
    predictions = predictions.copy()

    required_defaults = {
        "review_id": None,
        "sentiment_label": None,
        "sentiment_score": None,
    }

    for col, default in required_defaults.items():
        if col not in predictions.columns:
            predictions[col] = default

    predictions = predictions.dropna(subset=["review_id", "sentiment_label"])
    predictions = predictions.drop_duplicates(subset=["review_id"], keep="last")

    sql = text("""
        INSERT INTO review_analysis (
            review_id,
            sentiment_label,
            sentiment_score,
            model_name,
            feature_method,
            predicted_at
        )
        VALUES (
            :review_id,
            :sentiment_label,
            :sentiment_score,
            :model_name,
            :feature_method,
            CURRENT_TIMESTAMP
        );
    """)

    inserted = 0
    skipped = 0

    for _, row in predictions.iterrows():
        original_review_id = str(row.get("review_id"))
        db_review_id = review_map.get(original_review_id)

        if db_review_id is None:
            skipped += 1
            continue

        conn.execute(sql, {
            "review_id": db_review_id,
            "sentiment_label": row.get("sentiment_label"),
            "sentiment_score": None if pd.isna(row.get("sentiment_score")) else row.get("sentiment_score"),
            "model_name": "LogisticRegression",
            "feature_method": "TF-IDF",
        })

        inserted += 1

    print(f"Review analysis inserted: {inserted}")
    print(f"Review analysis skipped: {skipped}")


def main() -> None:
    if not OBJECTS_CSV.exists():
        raise FileNotFoundError(f"Not found: {OBJECTS_CSV}")

    if not REVIEWS_CSV.exists():
        raise FileNotFoundError(f"Not found: {REVIEWS_CSV}")

    objects = pd.read_csv(OBJECTS_CSV)
    reviews = pd.read_csv(REVIEWS_CSV)

    predictions = (
        pd.read_csv(SENTIMENT_CSV)
        if SENTIMENT_CSV.exists()
        else pd.DataFrame()
    )

    engine = get_engine()

    with engine.begin() as conn:
        prepare_database(conn)
        object_map = load_objects(conn, objects)
        review_map = load_reviews(conn, reviews, object_map)

        if not predictions.empty:
            load_review_analysis(conn, predictions, review_map)
        else:
            print("sentiment_predictions.csv not found; review_analysis was not loaded.")

    print("Upload to PostgreSQL completed.")


if __name__ == "__main__":
    main()