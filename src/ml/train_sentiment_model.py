from __future__ import annotations

import json
from pathlib import Path

import joblib
import pandas as pd
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, f1_score
from sklearn.model_selection import train_test_split
from sklearn.pipeline import Pipeline

from src.config import MODEL_REPORT_JSON, SENTIMENT_MODEL_PATH, TFIDF_VECTORIZER_PATH


def weak_label_from_rating(rating: float | int | None) -> str:
    if pd.isna(rating):
        return 'neutral'
    rating = float(rating)
    if rating >= 4.0:
        return 'positive'
    if rating <= 2.5:
        return 'negative'
    return 'neutral'


def prepare_training_data(corpus: pd.DataFrame) -> pd.DataFrame:
    df = corpus.copy()
    if 'sentiment_label' not in df.columns:
        df['sentiment_label'] = df['rating_normalized'].map(weak_label_from_rating)
    df = df[df['text_cleaned'].fillna('').astype(str).str.len() > 0]
    df = df[df['sentiment_label'].isin(['positive', 'neutral', 'negative'])]
    return df


def train_model(
    corpus_path: str | Path,
    model_path: str | Path = SENTIMENT_MODEL_PATH,
    vectorizer_path: str | Path = TFIDF_VECTORIZER_PATH,
    report_path: str | Path = MODEL_REPORT_JSON,
) -> dict:
    corpus = pd.read_csv(corpus_path)
    df = prepare_training_data(corpus)
    if len(df) < 3:
        raise ValueError('Not enough rows to train even a demo model. Need at least 3 valid corpus rows.')

    X = df['text_cleaned'].astype(str)
    y = df['sentiment_label'].astype(str)

    test_size = 0.3 if len(df) >= 10 else 0.34
    stratify = y if y.value_counts().min() >= 2 and y.nunique() > 1 else None
    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=test_size, random_state=42, stratify=stratify
    )

    vectorizer = TfidfVectorizer(ngram_range=(1, 2), min_df=1)
    classifier = LogisticRegression(max_iter=1000, class_weight='balanced')
    model = Pipeline([
        ('tfidf', vectorizer),
        ('clf', classifier),
    ])
    model.fit(X_train, y_train)
    y_pred = model.predict(X_test)

    report = {
        'model_name': 'LogisticRegression',
        'feature_method': 'TF-IDF',
        'train_size': int(len(X_train)),
        'test_size': int(len(X_test)),
        'accuracy': float(accuracy_score(y_test, y_pred)),
        'macro_f1': float(f1_score(y_test, y_pred, average='macro', zero_division=0)),
        'label_source': 'weak_rating_labels_if_manual_labels_absent',
    }

    model_path = Path(model_path)
    vectorizer_path = Path(vectorizer_path)
    report_path = Path(report_path)
    model_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.parent.mkdir(parents=True, exist_ok=True)

    joblib.dump(model, model_path)
    joblib.dump(model.named_steps['tfidf'], vectorizer_path)
    report_path.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    from src.config import CORPUS_CSV
    print(train_model(CORPUS_CSV))
