from __future__ import annotations

from typing import Any
import math


def normalize_rating(value: Any) -> float | None:
    """Normalize rating to a 0..5 scale.

    Common cases:
    - 0..5 stays unchanged;
    - 0..10 is divided by 2;
    - 0..100 is divided by 20.
    """
    if value is None or value == '':
        return None
    try:
        rating = float(str(value).replace(',', '.'))
    except ValueError:
        return None

    if math.isnan(rating):
        return None
    if rating < 0:
        return None
    if rating <= 5:
        return round(rating, 2)
    if rating <= 10:
        return round(rating / 2, 2)
    if rating <= 100:
        return round(rating / 20, 2)
    return None
