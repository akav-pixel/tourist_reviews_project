from __future__ import annotations

import json
from pathlib import Path
import pandas as pd


def load_json_records(path: str | Path, records_key: str | None = None) -> pd.DataFrame:
    path = Path(path)
    if not path.exists():
        raise FileNotFoundError(f'JSON file not found: {path}')

    data = json.loads(path.read_text(encoding='utf-8'))
    if records_key:
        data = data.get(records_key, [])
    if isinstance(data, dict):
        data = [data]
    if not isinstance(data, list):
        raise ValueError('JSON must contain a list of records or a records_key with a list')
    return pd.DataFrame(data)
