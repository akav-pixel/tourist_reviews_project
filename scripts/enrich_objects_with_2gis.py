from __future__ import annotations

import os
import sys
import time
from pathlib import Path
from urllib.parse import urlparse, parse_qs

import pandas as pd
import requests
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import OBJECTS_PROCESSED_CSV


API_URL = "https://catalog.api.2gis.com/3.0/items"


def clean_value(value) -> str:
    if pd.isna(value):
        return ""
    return str(value).strip()


def normalize_city(city: str) -> str:
    city = clean_value(city)
    aliases = {
        "Усть-Каменогорск": "Өскемен",
        "Усть Каменогорск": "Өскемен",
        "Каменогорск": "Өскемен",
        "Оскемен": "Өскемен",
        "Oskemen": "Өскемен",
        "Ust-Kamenogorsk": "Өскемен",
        "Ust Kamenogorsk": "Өскемен",
    }
    return aliases.get(city, city)


def extract_from_yandex_ll(url: str) -> tuple[float | None, float | None]:
    """
    Yandex ll = longitude,latitude.
    Возвращает latitude, longitude.
    """
    try:
        query = parse_qs(urlparse(str(url)).query)
        ll = query.get("ll", [None])[0]
        if not ll:
            return None, None

        lon_str, lat_str = ll.split(",", 1)
        longitude = float(lon_str)
        latitude = float(lat_str)
        return latitude, longitude
    except Exception:
        return None, None


def search_2gis_point(
    *,
    api_key: str,
    name: str,
    city: str,
) -> tuple[float | None, float | None, str, str]:
    """
    Ищет объект в 2GIS по названию и городу.
    Возвращает latitude, longitude, matched_name, matched_id.
    """
    query = f"{city} {name}".strip()

    params = {
        "q": query,
        "type": "branch,attraction,adm_div.place",
        "fields": "items.point,items.address,items.full_address_name",
        "locale": "ru_KZ",
        "page_size": 5,
        "key": api_key,
    }

    response = requests.get(API_URL, params=params, timeout=30)
    response.raise_for_status()

    data = response.json()
    items = data.get("result", {}).get("items", [])

    if not items:
        return None, None, "", ""

    item = items[0]
    point = item.get("point") or {}

    lon = point.get("lon")
    lat = point.get("lat")

    if lat is None or lon is None:
        return None, None, clean_value(item.get("name")), clean_value(item.get("id"))

    return (
        float(lat),
        float(lon),
        clean_value(item.get("name")),
        clean_value(item.get("id")),
    )


def main() -> None:
    load_dotenv()

    api_key = os.getenv("DGIS_API_KEY")
    if not api_key:
        raise RuntimeError("DGIS_API_KEY не найден. Добавь его в .env")

    if not OBJECTS_PROCESSED_CSV.exists():
        raise FileNotFoundError(f"Файл не найден: {OBJECTS_PROCESSED_CSV}")

    objects = pd.read_csv(OBJECTS_PROCESSED_CSV, encoding="utf-8-sig")

    objects.columns = (
        objects.columns
        .astype(str)
        .str.replace("\ufeff", "", regex=False)
        .str.strip()
    )

    for col in ["latitude", "longitude", "source_url"]:
        if col not in objects.columns:
            objects[col] = None

    if "city" in objects.columns:
        objects["city"] = objects["city"].apply(normalize_city)

    report_rows = []

    for idx, row in objects.iterrows():
        name = clean_value(row.get("name"))
        city = normalize_city(row.get("city"))

        current_lat = pd.to_numeric(row.get("latitude"), errors="coerce")
        current_lon = pd.to_numeric(row.get("longitude"), errors="coerce")

        if pd.notna(current_lat) and pd.notna(current_lon):
            report_rows.append({
                "name": name,
                "city": city,
                "status": "already_has_coordinates",
                "latitude": current_lat,
                "longitude": current_lon,
                "matched_name": "",
                "matched_id": "",
            })
            continue

        # 1) сначала пробуем взять координаты из Yandex URL
        source_url = clean_value(row.get("source_url"))
        lat, lon = extract_from_yandex_ll(source_url)

        if lat is not None and lon is not None:
            objects.at[idx, "latitude"] = lat
            objects.at[idx, "longitude"] = lon

            report_rows.append({
                "name": name,
                "city": city,
                "status": "from_yandex_url",
                "latitude": lat,
                "longitude": lon,
                "matched_name": "",
                "matched_id": "",
            })
            continue

        # 2) если в ссылке координат нет — ищем через 2GIS API
        try:
            lat, lon, matched_name, matched_id = search_2gis_point(
                api_key=api_key,
                name=name,
                city=city,
            )

            if lat is not None and lon is not None:
                objects.at[idx, "latitude"] = lat
                objects.at[idx, "longitude"] = lon

                status = "from_2gis_api"
            else:
                status = "not_found"

            report_rows.append({
                "name": name,
                "city": city,
                "status": status,
                "latitude": lat,
                "longitude": lon,
                "matched_name": matched_name,
                "matched_id": matched_id,
            })

            print(f"{status}: {name} -> {lat}, {lon} | {matched_name}")

        except Exception as exc:
            report_rows.append({
                "name": name,
                "city": city,
                "status": "error",
                "latitude": None,
                "longitude": None,
                "matched_name": "",
                "matched_id": "",
                "error": str(exc),
            })

            print(f"ERROR: {name}: {exc}")

        time.sleep(0.4)

    objects.to_csv(OBJECTS_PROCESSED_CSV, index=False, encoding="utf-8-sig")

    report = pd.DataFrame(report_rows)
    report_path = Path("data/processed/2gis_coordinates_report.csv")
    report.to_csv(report_path, index=False, encoding="utf-8-sig")

    print(f"Updated: {OBJECTS_PROCESSED_CSV}")
    print(f"Report: {report_path}")


if __name__ == "__main__":
    main()