from __future__ import annotations

from pathlib import Path
import pandas as pd


def build_corpus(reviews: pd.DataFrame, output_path: str | Path | None = None) -> pd.DataFrame:
    required = ['review_id', 'source_object_id', 'text_cleaned', 'rating_normalized', 'language', 'quality_status']
    missing = [c for c in required if c not in reviews.columns]
    if missing:
        raise ValueError(f'Missing columns for corpus: {missing}')

    corpus = reviews.loc[
        (reviews['quality_status'] == 'valid')
        & reviews['text_cleaned'].fillna('').astype(str).str.len().ge(10)
    ].copy()

    columns = [
        'review_id', 'source', 'source_object_id', 'text_cleaned',
        'rating_normalized', 'language', 'review_date'
    ]
    columns = [c for c in columns if c in corpus.columns]
    corpus = corpus[columns].reset_index(drop=True)

    if output_path:
        output_path = Path(output_path)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        corpus.to_csv(output_path, index=False, encoding='utf-8-sig')
    return corpus
