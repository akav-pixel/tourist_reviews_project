from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.importers.csv_importer import load_reviews_csv


class GoogleReviewImportAdapter:
    """Adapter for Google Maps review data obtained through permitted mechanisms."""

    def load_from_csv_export(self, path: str | Path) -> pd.DataFrame:
        return load_reviews_csv(path)
