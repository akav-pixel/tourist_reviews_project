from __future__ import annotations

from pathlib import Path
import pandas as pd

from src.importers.csv_importer import load_objects_csv


class GIS2ObjectLoader:
    """2GIS object loader adapter.

    Базовая версия принимает разрешённый экспорт, CSV/JSON или открытый датасет.
    Тяжёлый Selenium-сбор не запускается из dashboard и не рассматривается как
    обязательный способ получения данных.
    """

    def load_from_csv_export(self, path: str | Path) -> pd.DataFrame:
        return load_objects_csv(path)
