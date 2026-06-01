from __future__ import annotations

from pathlib import Path

import joblib
import pandas as pd

from src.config import SENTIMENT_MODEL_PATH, SENTIMENT_PREDICTIONS_CSV
from src.ml.train_sentiment_model import weak_label_from_rating


def predict_sentiment(
    corpus_path: str | Path,
    output_path: str | Path = SENTIMENT_PREDICTIONS_CSV,
    model_path: str | Path = SENTIMENT_MODEL_PATH,
) -> pd.DataFrame:
    corpus = pd.read_csv(corpus_path)
    model_path = Path(model_path)
    result = corpus.copy()

    if model_path.exists():
        model = joblib.load(model_path)
        labels = model.predict(result['text_cleaned'].fillna('').astype(str))
        result['sentiment_label'] = labels
        if hasattr(model.named_steps.get('clf'), 'predict_proba'):
            proba = model.predict_proba(result['text_cleaned'].fillna('').astype(str))
            result['sentiment_score'] = proba.max(axis=1).round(6)
        else:
            result['sentiment_score'] = None
        result['model_name'] = 'LogisticRegression'
        result['feature_method'] = 'TF-IDF'
    else:
        result['sentiment_label'] = result['rating_normalized'].map(weak_label_from_rating)
        result['sentiment_score'] = None
        result['model_name'] = 'weak_rating_rule'
        result['feature_method'] = 'rating_based_fallback'

    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    result.to_csv(output_path, index=False, encoding='utf-8-sig')
    return result


if __name__ == '__main__':
    from src.config import CORPUS_CSV
    predict_sentiment(CORPUS_CSV)
    print(f'Saved predictions to {SENTIMENT_PREDICTIONS_CSV}')
