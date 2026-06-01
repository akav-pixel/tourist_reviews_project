from __future__ import annotations

from pathlib import Path
from typing import Any

import pandas as pd


def classify_quality(row: pd.Series) -> str:
    text = str(row.get('text_cleaned') or '').strip()
    rating = row.get('rating_normalized')
    is_duplicate = bool(row.get('is_duplicate', False))

    if is_duplicate:
        return 'rejected'
    if len(text) >= 10 and pd.notna(rating):
        return 'valid'
    if len(text) >= 3 or pd.notna(rating):
        return 'limited'
    return 'rejected'


def mark_duplicates(df: pd.DataFrame) -> pd.Series:
    if df.empty:
        return pd.Series(dtype=bool)
    key_columns = [c for c in ['source_object_id', 'text_cleaned'] if c in df.columns]
    if not key_columns:
        key_columns = [c for c in ['text_cleaned'] if c in df.columns]
    return df.duplicated(subset=key_columns, keep='first')


def calculate_quality_indicators(df: pd.DataFrame) -> pd.DataFrame:
    total = len(df)
    if total == 0:
        rows = [
            ('K_tolyktyk', 0, 0, 'N_tolyk / N_zhalpy'),
            ('K_dubl', 0, 0, 'N_dubl / N_zhalpy'),
            ('K_zharamdy', 0, 0, 'N_korpus / N_zhinalgan'),
            ('K_unknown', 0, 0, 'N_unknown / N_zhalpy'),
        ]
    else:
        has_text = df.get('text_cleaned', pd.Series([''] * total)).fillna('').astype(str).str.len() >= 10
        has_rating = df.get('rating_normalized', pd.Series([None] * total)).notna()
        complete = int((has_text & has_rating).sum())
        duplicates = int(df.get('is_duplicate', pd.Series([False] * total)).fillna(False).sum())
        valid = int((df.get('quality_status', pd.Series(['limited'] * total)) == 'valid').sum())
        unknown = int((df.get('language', pd.Series(['unknown'] * total)) == 'unknown').sum())
        rows = [
            ('K_tolyktyk', complete, total, 'N_tolyk / N_zhalpy'),
            ('K_dubl', duplicates, total, 'N_dubl / N_zhalpy'),
            ('K_zharamdy', valid, total, 'N_korpus / N_zhinalgan'),
            ('K_unknown', unknown, total, 'N_unknown / N_zhalpy'),
        ]

    report = pd.DataFrame(rows, columns=['metric', 'numerator', 'denominator', 'formula'])
    report['value'] = report.apply(
        lambda r: round(float(r['numerator']) / float(r['denominator']), 4) if r['denominator'] else 0.0,
        axis=1,
    )
    return report[['metric', 'formula', 'numerator', 'denominator', 'value']]


def save_quality_report(df: pd.DataFrame, output_path: str | Path) -> pd.DataFrame:
    report = calculate_quality_indicators(df)
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    report.to_csv(output_path, index=False, encoding='utf-8-sig')
    return report
