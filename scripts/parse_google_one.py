from __future__ import annotations

import argparse
import hashlib
import json
import re
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd
from selenium import webdriver
from selenium.common.exceptions import WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from src.config import OBJECTS_PROCESSED_CSV, REVIEWS_PROCESSED_CSV
from src.preprocessing.pipeline import preprocess_objects, preprocess_reviews
from src.reconciliation.object_matcher import add_canonical_key


RAW_DIR = Path("data/raw/google_maps")


@dataclass
class GoogleConfig:
    url: str
    name: str
    city: str
    object_type: str
    limit: int = 50
    scrolls: int = 40
    headless: bool = False


def normalize_city(city: str) -> str:
    city = str(city or "").strip()
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


def clean_text(value: Any) -> str:
    return re.sub(r"\s+", " ", str(value or "")).strip()


def extract_source_object_id(url: str) -> str:
    """
    Для Google Maps пытаемся взять внутренний идентификатор из URL.
    Если не нашли — создаём стабильный hash.
    """
    patterns = [
        r"!1s([^!]+)",
        r"cid=([0-9]+)",
        r"place_id=([^&]+)",
    ]

    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            raw_id = match.group(1)
            safe_id = re.sub(r"[^a-zA-Z0-9_:-]", "_", raw_id)
            return safe_id[:80]

    return hashlib.sha1(url.encode("utf-8")).hexdigest()[:16]


def make_review_id(source_object_id: str, author: str, date_raw: str, text: str, rating: float | None) -> str:
    key = f"{source_object_id}|{author}|{date_raw}|{text}|{rating}"
    digest = hashlib.sha1(key.encode("utf-8")).hexdigest()[:20]
    return f"google_maps_{source_object_id}_{digest}"


def parse_rating(value: str) -> float | None:
    value = str(value or "")
    match = re.search(r"(\d+(?:[,.]\d+)?)", value)
    if not match:
        return None
    try:
        return float(match.group(1).replace(",", "."))
    except ValueError:
        return None


def create_driver(headless: bool) -> webdriver.Chrome:
    options = Options()

    if headless:
        options.add_argument("--headless=new")

    options.add_argument("--window-size=1400,1000")
    options.add_argument("--lang=ru-RU")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)
    return driver


def click_google_buttons(driver: webdriver.Chrome) -> None:
    """
    Закрывает возможные окна и нажимает кнопки раскрытия текста.
    """
    button_selectors = [
        "button[aria-label*='Принять']",
        "button[aria-label*='Accept']",
        "button[aria-label*='Согласен']",
        "button[aria-label*='Ещё']",
        "button[aria-label*='Еще']",
        "button[aria-label*='More']",
        "button.w8nwRe",
    ]

    for selector in button_selectors:
        buttons = driver.find_elements(By.CSS_SELECTOR, selector)
        for button in buttons[:30]:
            try:
                if button.is_displayed() and button.is_enabled():
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.15)
            except Exception:
                pass


def find_scroll_container(driver: webdriver.Chrome):
    """
    Ищет прокручиваемый блок отзывов Google Maps.
    """
    candidates = driver.find_elements(By.CSS_SELECTOR, "div.m6QErb.DxyBCb.kA9KIf.dS8AEf")
    for el in candidates:
        try:
            scroll_height = driver.execute_script("return arguments[0].scrollHeight", el)
            client_height = driver.execute_script("return arguments[0].clientHeight", el)
            if scroll_height and client_height and scroll_height > client_height:
                return el
        except Exception:
            pass

    try:
        return driver.execute_script(
            """
            const divs = Array.from(document.querySelectorAll('div'));
            const scrollables = divs
              .filter(e => e.scrollHeight > e.clientHeight + 300)
              .sort((a, b) => b.scrollHeight - a.scrollHeight);
            return scrollables[0] || document.scrollingElement;
            """
        )
    except Exception:
        return None


def open_reviews_if_needed(driver: webdriver.Chrome) -> None:
    """
    Если ссылка открыла карточку объекта, пытаемся перейти во вкладку отзывов.
    """
    review_buttons = driver.find_elements(
        By.XPATH,
        "//button[contains(., 'Отзывы') or contains(., 'Reviews') or contains(., 'Пікірлер')]"
    )
    for button in review_buttons:
        try:
            if button.is_displayed() and button.is_enabled():
                driver.execute_script("arguments[0].click();", button)
                time.sleep(2)
                return
        except Exception:
            pass


def scroll_reviews(driver: webdriver.Chrome, limit: int, scrolls: int) -> None:
    container = find_scroll_container(driver)
    if container is None:
        return

    stable_rounds = 0
    last_count = 0

    for i in range(scrolls):
        click_google_buttons(driver)

        cards = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf")
        current_count = len(cards)

        print(f"Scroll {i + 1}/{scrolls}: cards={current_count}")

        if current_count >= limit:
            break

        if current_count == last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0
            last_count = current_count

        if stable_rounds >= 18:
            print("No new cards loaded. Stop scrolling.")
            break

        try:
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", container)
        except WebDriverException:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight)")

        time.sleep(1.4)


def extract_card(card, source_object_id: str, url: str) -> dict[str, Any] | None:
    try:
        author = ""
        for selector in [".d4r55", ".WNxzHc"]:
            items = card.find_elements(By.CSS_SELECTOR, selector)
            if items:
                author = clean_text(items[0].text)
                break

        rating = None
        rating_items = card.find_elements(By.CSS_SELECTOR, "span.kvMYJc, span[aria-label*='зв'], span[aria-label*='star']")
        for item in rating_items:
            aria = item.get_attribute("aria-label")
            rating = parse_rating(aria)
            if rating is not None:
                break

        date_raw = ""
        date_items = card.find_elements(By.CSS_SELECTOR, ".rsqaWe")
        if date_items:
            date_raw = clean_text(date_items[0].text)

        text_value = ""
        text_items = card.find_elements(By.CSS_SELECTOR, ".wiI7pd")
        if text_items:
            text_value = clean_text(text_items[0].text)

        if not text_value:
            return None

        if not author:
            author = "anonymous"

        review_id = card.get_attribute("data-review-id")
        if not review_id:
            review_id = make_review_id(source_object_id, author, date_raw, text_value, rating)
        else:
            review_id = f"google_maps_{source_object_id}_{review_id}"

        return {
            "source": "google_maps",
            "source_object_id": source_object_id,
            "review_id": review_id,
            "author": author,
            "review_text": text_value,
            "rating": rating,
            "review_date": None,
            "review_date_raw": date_raw,
            "url": url,
        }

    except Exception:
        return None


def parse_google_reviews(config: GoogleConfig) -> dict[str, Any]:
    source_object_id = extract_source_object_id(config.url)

    driver = create_driver(config.headless)

    try:
        driver.get(config.url)
        time.sleep(5)

        click_google_buttons(driver)
        open_reviews_if_needed(driver)
        time.sleep(2)

        scroll_reviews(driver, config.limit, config.scrolls)
        click_google_buttons(driver)

        cards = driver.find_elements(By.CSS_SELECTOR, "div.jftiEf")
        print(f"Found cards: {len(cards)}")

        reviews = []
        seen = set()

        for card in cards:
            item = extract_card(card, source_object_id, config.url)
            if not item:
                continue

            if item["review_id"] in seen:
                continue

            seen.add(item["review_id"])
            reviews.append(item)

            if len(reviews) >= config.limit:
                break

        return {
            "meta": {
                "source": "google_maps",
                "source_object_id": source_object_id,
                "source_url": config.url,
                "name": config.name,
                "city": config.city,
                "type": config.object_type,
                "limit": config.limit,
                "scrolls": config.scrolls,
                "parsed_count": len(reviews),
            },
            "reviews": reviews,
        }

    finally:
        driver.quit()


def save_raw_result(result: dict[str, Any]) -> tuple[Path, Path]:
    RAW_DIR.mkdir(parents=True, exist_ok=True)

    source_object_id = result["meta"]["source_object_id"]

    json_path = RAW_DIR / f"google_{source_object_id}_reviews.json"
    csv_path = RAW_DIR / f"google_{source_object_id}_reviews.csv"

    json_path.write_text(
        json.dumps(result, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    pd.DataFrame(result.get("reviews", [])).to_csv(
        csv_path,
        index=False,
        encoding="utf-8-sig",
    )

    return json_path, csv_path


def append_to_processed(result: dict[str, Any]) -> None:
    meta = result["meta"]
    source_object_id = str(meta["source_object_id"])

    new_object = pd.DataFrame(
        [
            {
                "source": "google_maps",
                "source_object_id": source_object_id,
                "name": meta["name"],
                "type": meta["type"],
                "city": normalize_city(meta["city"]),
                "source_url": meta["source_url"],
                "latitude": None,
                "longitude": None,
            }
        ]
    )

    new_reviews = pd.DataFrame(result.get("reviews", []))

    if new_reviews.empty:
        print("No reviews to save.")
        return

    if OBJECTS_PROCESSED_CSV.exists():
        old_objects = pd.read_csv(OBJECTS_PROCESSED_CSV)
    else:
        old_objects = pd.DataFrame()

    if REVIEWS_PROCESSED_CSV.exists():
        old_reviews = pd.read_csv(REVIEWS_PROCESSED_CSV)
    else:
        old_reviews = pd.DataFrame()

    objects_all = pd.concat([old_objects, new_object], ignore_index=True)
    reviews_all = pd.concat([old_reviews, new_reviews], ignore_index=True)

    objects_all["source"] = objects_all["source"].astype(str)
    objects_all["source_object_id"] = objects_all["source_object_id"].astype(str)

    reviews_all["source"] = reviews_all["source"].astype(str)
    reviews_all["source_object_id"] = reviews_all["source_object_id"].astype(str)

    objects_all = objects_all.drop_duplicates(
        subset=["source", "source_object_id"],
        keep="last",
    )

    reviews_all = reviews_all.drop_duplicates(
        subset=["source", "review_id"],
        keep="last",
    )

    objects_processed = add_canonical_key(preprocess_objects(objects_all))
    reviews_processed = preprocess_reviews(reviews_all)

    mask = reviews_processed["review_id"].astype(str).str.startswith(
        f"google_maps_{source_object_id}_"
    )

    reviews_processed.loc[mask, "source"] = "google_maps"
    reviews_processed.loc[mask, "source_object_id"] = source_object_id
    reviews_processed.loc[mask, "url"] = meta["source_url"]

    object_mask = (
        (objects_processed["source"].astype(str) == "google_maps")
        & (objects_processed["source_object_id"].astype(str) == source_object_id)
    )

    objects_processed.loc[object_mask, "name"] = meta["name"]
    objects_processed.loc[object_mask, "type"] = meta["type"]
    objects_processed.loc[object_mask, "city"] = normalize_city(meta["city"])
    objects_processed.loc[object_mask, "source_url"] = meta["source_url"]

    OBJECTS_PROCESSED_CSV.parent.mkdir(parents=True, exist_ok=True)

    objects_processed.to_csv(
        OBJECTS_PROCESSED_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    reviews_processed.to_csv(
        REVIEWS_PROCESSED_CSV,
        index=False,
        encoding="utf-8-sig",
    )

    print(f"Processed objects saved: {OBJECTS_PROCESSED_CSV}")
    print(f"Processed reviews saved: {REVIEWS_PROCESSED_CSV}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Parse one Google Maps object reviews")
    parser.add_argument("--url", required=True)
    parser.add_argument("--name", required=True)
    parser.add_argument("--city", required=True)
    parser.add_argument("--type", required=True)
    parser.add_argument("--limit", type=int, default=50)
    parser.add_argument("--scrolls", type=int, default=40)
    parser.add_argument("--visible", action="store_true")

    args = parser.parse_args()

    config = GoogleConfig(
        url=args.url,
        name=args.name,
        city=args.city,
        object_type=args.type,
        limit=args.limit,
        scrolls=args.scrolls,
        headless=not args.visible,
    )

    result = parse_google_reviews(config)
    json_path, csv_path = save_raw_result(result)

    print(f"Raw JSON saved: {json_path}")
    print(f"Raw CSV saved: {csv_path}")
    print(f"Parsed reviews: {len(result.get('reviews', []))}")

    append_to_processed(result)


if __name__ == "__main__":
    main()