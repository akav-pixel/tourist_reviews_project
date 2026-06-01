from __future__ import annotations

from pathlib import Path
from typing import Iterable

import pandas as pd
from sqlalchemy import text
from sqlalchemy.engine import Engine


class Repository:
    """Thin repository layer for PostgreSQL operations.

    The class keeps DB access isolated from preprocessing, ML and dashboard logic.
    """

    def __init__(self, engine: Engine):
        self.engine = engine

    def execute_schema(self, schema_path: str | Path) -> None:
        sql = Path(schema_path).read_text(encoding='utf-8')
        with self.engine.begin() as conn:
            conn.execute(text(sql))

    def read_dataframe(self, sql: str, params: dict | None = None) -> pd.DataFrame:
        with self.engine.connect() as conn:
            return pd.read_sql_query(text(sql), conn, params=params or {})

    def append_dataframe(self, df: pd.DataFrame, table_name: str) -> int:
        if df.empty:
            return 0
        df.to_sql(table_name, self.engine, if_exists='append', index=False, method='multi')
        return len(df)

    def get_dashboard_dataset(self) -> pd.DataFrame:
        sql = """
        SELECT
            r.id AS review_db_id,
            r.review_id,
            r.review_text,
            r.text_cleaned,
            r.rating,
            r.rating_normalized,
            r.review_date,
            r.language,
            r.quality_status,
            r.is_duplicate,
            r.source AS review_source,
            o.name AS object_name,
            o.type AS object_type,
            o.city,
            o.latitude,
            o.longitude,
            a.sentiment_label,
            a.sentiment_score
        FROM reviews r
        JOIN tourist_objects o ON o.id = r.object_id
        LEFT JOIN review_analysis a ON a.review_id = r.id
        """
        return self.read_dataframe(sql)
