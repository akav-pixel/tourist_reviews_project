from __future__ import annotations

import pandas as pd

from src.preprocessing.text_cleaner import normalize_name


def add_canonical_key(objects: pd.DataFrame) -> pd.DataFrame:
    """Create a simple canonical key for object reconciliation.

    In a full version this can be replaced by fuzzy matching using name, city,
    coordinates and object type.
    """
    df = objects.copy()
    if 'normalized_name' not in df.columns:
        df['normalized_name'] = df['name'].map(normalize_name)
    df['canonical_key'] = (
        df['city'].fillna('').astype(str).str.lower().str.strip()
        + '|'
        + df['type'].fillna('').astype(str).str.lower().str.strip()
        + '|'
        + df['normalized_name'].fillna('').astype(str)
    )
    return df
