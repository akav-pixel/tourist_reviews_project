from __future__ import annotations

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine

from src.config import DATABASE_URL


def get_engine(database_url: str | None = None) -> Engine:
    """Create SQLAlchemy engine for PostgreSQL.

    In Streamlit Cloud pass DATABASE_URL through secrets or environment variables.
    """
    url = database_url or DATABASE_URL
    return create_engine(url, pool_pre_ping=True, future=True)
