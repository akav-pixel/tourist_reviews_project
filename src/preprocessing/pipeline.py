from __future__ import annotations

import pandas as pd

from src.preprocessing.language_detector import detect_language
from src.preprocessing.quality_metrics import classify_quality, mark_duplicates
from src.preprocessing.rating_normalizer import normalize_rating
from src.preprocessing.text_cleaner import clean_text, normalize_name


def preprocess_objects(objects: pd.DataFrame) -> pd.DataFrame:
    df = objects.copy()
    df['name'] = df['name'].map(clean_text)
    df['type'] = df.get('type', '').map(clean_text)
    df['city'] = df.get('city', '').map(clean_text)
    df['normalized_name'] = df['name'].map(normalize_name)
    for col in ['latitude', 'longitude']:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors='coerce')
    return df


def preprocess_reviews(reviews: pd.DataFrame) -> pd.DataFrame:
    df = reviews.copy()
    df['review_text'] = df.get('review_text', '').fillna('').astype(str)
    df['text_cleaned'] = df['review_text'].map(clean_text)
    df['rating_normalized'] = df.get('rating', None).map(normalize_rating) if 'rating' in df.columns else None
    df['language'] = df['text_cleaned'].map(detect_language)
    if 'review_date' in df.columns:
        df['review_date'] = pd.to_datetime(df['review_date'], errors='coerce').dt.date
    df['is_duplicate'] = mark_duplicates(df)
    df['quality_status'] = df.apply(classify_quality, axis=1)
    return df
