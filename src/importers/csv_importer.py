from __future__ import annotations

from pathlib import Path
import pandas as pd


def load_csv(path: str | Path) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'CSV file not found: {path}')
    return pd.read_csv(path)


def normalize_columns(df: pd.DataFrame) -> pd.DataFrame:
    result = df.copy()
    result.columns = [str(c).strip().lower() for c in result.columns]
    return result


def load_objects_csv(path: str | Path) -> pd.DataFrame:
    df = normalize_columns(load_csv(path))
    required = {'source', 'source_object_id', 'name', 'type', 'city'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing object columns: {sorted(missing)}')
    return df


def load_reviews_csv(path: str | Path) -> pd.DataFrame:
    df = normalize_columns(load_csv(path))
    required = {'source', 'review_id', 'source_object_id', 'review_text'}
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f'Missing review columns: {sorted(missing)}')
    return df
