from __future__ import annotations

import argparse

from src.config import (
    CORPUS_CSV,
    OBJECTS_PROCESSED_CSV,
    QUALITY_REPORT_CSV,
    REVIEWS_PROCESSED_CSV,
    SAMPLE_OBJECTS_CSV,
    SAMPLE_REVIEWS_CSV,
)
from src.corpus.corpus_builder import build_corpus
from src.importers.csv_importer import load_objects_csv, load_reviews_csv
from src.ml.predict_sentiment import predict_sentiment
from src.ml.train_sentiment_model import train_model
from src.preprocessing.pipeline import preprocess_objects, preprocess_reviews
from src.preprocessing.quality_metrics import save_quality_report
from src.reconciliation.object_matcher import add_canonical_key


def preprocess_sample() -> None:
    objects = load_objects_csv(SAMPLE_OBJECTS_CSV)
    reviews = load_reviews_csv(SAMPLE_REVIEWS_CSV)

    objects_processed = add_canonical_key(preprocess_objects(objects))
    reviews_processed = preprocess_reviews(reviews)

    objects_processed.to_csv(OBJECTS_PROCESSED_CSV, index=False, encoding="utf-8-sig")
    reviews_processed.to_csv(REVIEWS_PROCESSED_CSV, index=False, encoding="utf-8-sig")

    print(f"Saved: {OBJECTS_PROCESSED_CSV}")
    print(f"Saved: {REVIEWS_PROCESSED_CSV}")


def build_corpus_command() -> None:
    import pandas as pd

    reviews = pd.read_csv(REVIEWS_PROCESSED_CSV)
    corpus = build_corpus(reviews, CORPUS_CSV)

    print(f"Saved: {CORPUS_CSV} rows={len(corpus)}")


def evaluate_quality_command() -> None:
    import pandas as pd

    reviews = pd.read_csv(REVIEWS_PROCESSED_CSV)
    report = save_quality_report(reviews, QUALITY_REPORT_CSV)

    print(report.to_string(index=False))
    print(f"Saved: {QUALITY_REPORT_CSV}")


def train_model_command() -> None:
    report = train_model(CORPUS_CSV)
    print(report)


def predict_sentiment_command() -> None:
    result = predict_sentiment(CORPUS_CSV)
    print(f"Saved sentiment predictions rows={len(result)}")


def run_sample_pipeline() -> None:
    preprocess_sample()
    evaluate_quality_command()
    build_corpus_command()
    train_model_command()
    predict_sentiment_command()


def run_yandex_command(args: argparse.Namespace) -> None:
    """
    Запускает отдельный ingestion pipeline для Яндекс Карт.

    Важно:
    - этот парсер не должен запускаться из Streamlit dashboard;
    - он запускается локально как отдельный этап сбора данных;
    - результат сохраняется в data/raw/yandex и data/processed.
    """
    from src.parsers.yandex_live.pipeline import run_yandex_live_pipeline

    objects, reviews = run_yandex_live_pipeline(
        url=args.url,
        name=args.name,
        city=args.city,
        object_type=args.type,
        limit=args.limit,
        headless=not args.visible,
        scrolls=args.scrolls,
        save_debug_html=args.debug_html,
    )

    print(f"Saved: {OBJECTS_PROCESSED_CSV} rows={len(objects)}")
    print(f"Saved: {REVIEWS_PROCESSED_CSV} rows={len(reviews)}")

    evaluate_quality_command()
    build_corpus_command()
    train_model_command()
    predict_sentiment_command()


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Tourist reviews diploma project CLI"
    )

    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("preprocess-sample")
    sub.add_parser("evaluate-quality")
    sub.add_parser("build-corpus")
    sub.add_parser("train-model")
    sub.add_parser("predict-sentiment")
    sub.add_parser("run-sample-pipeline")

    yandex = sub.add_parser(
        "parse-yandex",
        help="Run local Yandex Maps ingestion pipeline",
    )

    yandex.add_argument(
        "--url",
        required=True,
        help="Yandex Maps organization reviews URL",
    )

    yandex.add_argument(
        "--name",
        required=True,
        help="Tourist object name",
    )

    yandex.add_argument(
        "--city",
        required=True,
        help="City name",
    )

    yandex.add_argument(
        "--type",
        default="cultural_object",
        help="museum, hotel, attraction, cultural_object",
    )

    yandex.add_argument(
        "--limit",
        type=int,
        default=100,
        help="Maximum number of reviews to collect",
    )

    yandex.add_argument(
        "--scrolls",
        type=int,
        default=25,
        help="Number of scroll actions in reviews block",
    )

    yandex.add_argument(
        "--visible",
        action="store_true",
        help="Show Chrome window instead of headless mode",
    )

    yandex.add_argument(
        "--debug-html",
        action="store_true",
        help="Save page html to data/debug",
    )

    args = parser.parse_args()

    commands = {
        "preprocess-sample": preprocess_sample,
        "evaluate-quality": evaluate_quality_command,
        "build-corpus": build_corpus_command,
        "train-model": train_model_command,
        "predict-sentiment": predict_sentiment_command,
        "run-sample-pipeline": run_sample_pipeline,
    }

    if args.command == "parse-yandex":
        run_yandex_command(args)
    else:
        commands[args.command]()


if __name__ == "__main__":
    main()