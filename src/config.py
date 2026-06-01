from __future__ import annotations

import os
from pathlib import Path
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parents[1]
load_dotenv(BASE_DIR / '.env')

DATA_DIR = BASE_DIR / 'data'
RAW_DIR = DATA_DIR / 'raw'
PROCESSED_DIR = DATA_DIR / 'processed'
LOGS_DIR = DATA_DIR / 'logs'
DATABASE_DIR = BASE_DIR / 'database'
MODELS_DIR = BASE_DIR / 'models'

SAMPLE_OBJECTS_CSV = RAW_DIR / 'sample_objects.csv'
SAMPLE_REVIEWS_CSV = RAW_DIR / 'sample_reviews.csv'
OBJECTS_PROCESSED_CSV = PROCESSED_DIR / 'objects_processed.csv'
REVIEWS_PROCESSED_CSV = PROCESSED_DIR / 'reviews_processed.csv'
CORPUS_CSV = PROCESSED_DIR / 'corpus_reviews.csv'
QUALITY_REPORT_CSV = PROCESSED_DIR / 'quality_report.csv'
SENTIMENT_PREDICTIONS_CSV = PROCESSED_DIR / 'sentiment_predictions.csv'
MODEL_REPORT_JSON = PROCESSED_DIR / 'model_report.json'

SENTIMENT_MODEL_PATH = MODELS_DIR / 'sentiment_model.pkl'
TFIDF_VECTORIZER_PATH = MODELS_DIR / 'tfidf_vectorizer.pkl'

DATABASE_URL = os.getenv(
    'DATABASE_URL',
    'postgresql+psycopg2://postgres:postgres@localhost:5432/tourist_reviews'
)

SUPPORTED_LANGUAGES = {'ru', 'kk', 'mixed', 'unknown'}
QUALITY_STATUSES = {'valid', 'limited', 'rejected'}
SENTIMENT_LABELS = {'positive', 'neutral', 'negative', 'unknown'}

for directory in [RAW_DIR, PROCESSED_DIR, LOGS_DIR, MODELS_DIR]:
    directory.mkdir(parents=True, exist_ok=True)
