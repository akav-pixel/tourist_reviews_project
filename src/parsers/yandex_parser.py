from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.importers.csv_importer import load_reviews_csv


class YandexReviewImportAdapter:
    """Adapter for Yandex review data obtained legally.

    In the diploma text use cautious wording: API, export, CSV/JSON import or open datasets.
    """

    def load_from_csv_export(self, path: str | Path) -> pd.DataFrame:
        return load_reviews_csv(path)
