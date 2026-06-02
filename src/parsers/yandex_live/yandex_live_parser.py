from __future__ import annotations

import hashlib
import json
import re
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.common.exceptions import JavascriptException, TimeoutException, WebDriverException
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait


@dataclass
class YandexParserConfig:
    url: str
    city: str
    object_type: str
    limit: int = 100
    headless: bool = True
    wait_seconds: int = 20
    scrolls: int = 25
    sleep_between_scrolls: float = 1.0
    user_data_dir: str | None = None
    profile_directory: str | None = None
    raw_dir: str = "data/raw/yandex"
    debug_dir: str = "data/debug"
    save_debug_html: bool = False


def extract_source_object_id(url: str) -> str:
    """
    Извлекает ID организации из ссылки Яндекс Карт.

    Пример:
    https://yandex.kz/maps/org/qazaqstan_stelasy/41388584750/reviews/
    -> 41388584750
    """
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p]

    for part in parts:
        if part.isdigit() and len(part) >= 6:
            return part

    match = re.search(r"/org/[^/]+/(\d+)", url)
    if match:
        return match.group(1)

    digest = hashlib.md5(url.encode("utf-8")).hexdigest()[:12]
    return f"unknown_{digest}"


def make_review_id(
    source_object_id: str,
    author: str,
    text: str,
    date: str | None,
    rating: float | None,
) -> str:
    """
    Создаёт стабильный review_id на основе содержимого отзыва.
    """
    raw = f"{source_object_id}|{author}|{text}|{date or ''}|{rating or ''}"
    digest = hashlib.md5(raw.encode("utf-8")).hexdigest()[:16]
    return f"yandex_{source_object_id}_{digest}"


def clean_review_text(text: str) -> str:
    text = str(text or "")
    text = re.sub(r"\s+", " ", text)
    text = text.replace("… Ещё", "")
    text = text.replace("… Еще", "")
    text = text.replace("Ещё", "")
    text = text.replace("Еще", "")
    text = text.strip()
    return text


def is_noise_text(text: str) -> bool:
    """
    Отсекает строки профиля автора и технический мусор.
    """
    text = str(text or "").strip()

    if not text:
        return True

    if len(text) < 25:
        return True

    low = text.lower()

    if low in {"anonymous", "подписаться", "ещё", "еще"}:
        return True

    # Профильная строка, а не отзыв
    if "знаток города" in low and len(text) < 120:
        return True

    # Если это почти только профиль автора
    if "знаток города" in low and "подписаться" in low and len(text) < 160:
        return True

    return False


def safe_float(value: str | None) -> float | None:
    if value is None:
        return None

    value = str(value).replace(",", ".").strip()

    try:
        return float(value)
    except ValueError:
        return None


def extract_rating_from_card(soup: BeautifulSoup) -> float | None:
    """
    Извлекает рейтинг из карточки отзыва.

    Основной способ:
    <meta itemprop="ratingValue" content="5.0">

    Резервный способ:
    aria-label="Оценка 5 Из 5"
    """
    rating_meta = soup.select_one("[itemprop='ratingValue']")

    if rating_meta and rating_meta.get("content"):
        rating = safe_float(rating_meta.get("content"))
        if rating is not None:
            return rating

    rating_node = soup.select_one(".business-rating-badge-view__stars")
    if rating_node:
        aria_label = rating_node.get("aria-label", "")
        match = re.search(r"Оценка\s+([0-9]+(?:[.,][0-9]+)?)", aria_label)
        if match:
            return safe_float(match.group(1))

    return None


def extract_author_from_card(soup: BeautifulSoup) -> str:
    author_tag = soup.select_one(".business-review-view__author-name [itemprop='name']")

    if author_tag:
        author = author_tag.get_text(" ", strip=True)
        if author:
            return author

    author_link = soup.select_one(".business-review-view__author-name a")

    if author_link:
        author = author_link.get_text(" ", strip=True)
        if author:
            return author

    return "anonymous"


def extract_date_from_card(soup: BeautifulSoup) -> str | None:
    date_meta = soup.select_one("[itemprop='datePublished']")

    if date_meta and date_meta.get("content"):
        return date_meta.get("content")

    date_span = soup.select_one(".business-review-view__date span")

    if date_span:
        date_text = date_span.get_text(" ", strip=True)
        return date_text or None

    return None


def extract_text_from_card(soup: BeautifulSoup) -> str:
    """
    Берёт только тело отзыва, а не весь текст карточки.
    """
    body = soup.select_one(".business-review-view__body[itemprop='reviewBody']")

    if body is None:
        body = soup.select_one("[itemprop='reviewBody']")

    if body is None:
        return ""

    text = body.get_text(" ", strip=True)
    return clean_review_text(text)


def extract_review_from_card(
    card_html: str,
    source_object_id: str,
    source_url: str,
) -> dict[str, Any] | None:
    """
    Преобразует одну HTML-карточку отзыва в одну строку данных.
    """
    soup = BeautifulSoup(card_html, "html.parser")

    author = extract_author_from_card(soup)
    rating = extract_rating_from_card(soup)
    review_date = extract_date_from_card(soup)
    review_text = extract_text_from_card(soup)

    if is_noise_text(review_text):
        return None

    review_id = make_review_id(
        source_object_id=source_object_id,
        author=author,
        text=review_text,
        date=review_date,
        rating=rating,
    )

    return {
        "source": "yandex",
        "review_id": review_id,
        "source_object_id": str(source_object_id),
        "author": author,
        "review_text": review_text,
        "rating": rating,
        "review_date": review_date,
        "url": source_url,
    }


def create_driver(config: YandexParserConfig) -> webdriver.Chrome:
    options = Options()

    if config.headless:
        options.add_argument("--headless=new")

    options.add_argument("--disable-gpu")
    options.add_argument("--disable-software-rasterizer")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--no-sandbox")
    options.add_argument("--window-size=1440,1200")
    options.add_argument("--lang=ru-RU")
    options.add_argument("--disable-blink-features=AutomationControlled")

    if config.user_data_dir:
        options.add_argument(f"--user-data-dir={config.user_data_dir}")

    if config.profile_directory:
        options.add_argument(f"--profile-directory={config.profile_directory}")

    driver = webdriver.Chrome(options=options)
    driver.set_page_load_timeout(60)

    return driver


def close_popups(driver: webdriver.Chrome) -> None:
    """
    Пытается закрыть возможные всплывающие окна.
    """
    candidates = [
        "button[aria-label='Закрыть']",
        "button[aria-label='Close']",
        ".button._view_clear",
        ".modal__close",
    ]

    for selector in candidates:
        try:
            buttons = driver.find_elements(By.CSS_SELECTOR, selector)
            for button in buttons[:3]:
                if button.is_displayed():
                    driver.execute_script("arguments[0].click();", button)
                    time.sleep(0.3)
        except WebDriverException:
            continue


def find_scrollable_reviews_container(driver: webdriver.Chrome):
    """
    На Яндекс Картах отзывы находятся внутри прокручиваемой панели.
    Эта функция ищет наиболее подходящий scrollable-контейнер.
    """
    script = """
    const candidates = Array.from(document.querySelectorAll('div'));
    const scored = candidates
        .filter(el => el.scrollHeight > el.clientHeight + 200)
        .map(el => {
            const rect = el.getBoundingClientRect();
            const text = el.innerText || '';
            let score = 0;
            if (text.includes('Отзывы')) score += 5;
            if (text.includes('Знаток города')) score += 5;
            if (el.querySelector('.business-review-view__info')) score += 10;
            score += Math.min(10, Math.floor(el.scrollHeight / 1000));
            return {el, score, height: el.scrollHeight};
        })
        .sort((a, b) => b.score - a.score || b.height - a.height);

    return scored.length ? scored[0].el : null;
    """

    try:
        return driver.execute_script(script)
    except JavascriptException:
        return None


def click_more_buttons(driver: webdriver.Chrome) -> None:
    """
    Пытается раскрыть сокращённые отзывы.
    """
    selectors = [
        "button",
        ".spoiler-view__button",
        ".business-review-view__expand",
    ]

    for selector in selectors:
        try:
            elements = driver.find_elements(By.CSS_SELECTOR, selector)

            for element in elements:
                text = element.text.strip().lower()

                if text in {"ещё", "еще", "читать полностью", "показать полностью"}:
                    try:
                        driver.execute_script("arguments[0].click();", element)
                        time.sleep(0.15)
                    except WebDriverException:
                        pass
        except WebDriverException:
            pass


def scroll_reviews(driver: webdriver.Chrome, config: YandexParserConfig) -> None:
    """
    Скроллит панель отзывов.
    """
    last_count = 0
    stable_rounds = 0

    for _ in range(config.scrolls):
        close_popups(driver)
        click_more_buttons(driver)

        cards = driver.find_elements(By.CSS_SELECTOR, ".business-review-view__info")
        current_count = len(cards)

        if current_count >= config.limit:
            break

        if current_count == last_count:
            stable_rounds += 1
        else:
            stable_rounds = 0

        last_count = current_count

        if stable_rounds >= 5:
            break

        container = find_scrollable_reviews_container(driver)

        try:
            if container is not None:
                driver.execute_script(
                    "arguments[0].scrollTop = arguments[0].scrollHeight;",
                    container,
                )
            else:
                driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        except WebDriverException:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

        time.sleep(config.sleep_between_scrolls)


def wait_for_reviews(driver: webdriver.Chrome, wait_seconds: int) -> None:
    wait = WebDriverWait(driver, wait_seconds)

    try:
        wait.until(
            EC.presence_of_element_located(
                (By.CSS_SELECTOR, ".business-review-view__info")
            )
        )
    except TimeoutException:
        # Если отзывы не появились, всё равно дадим HTML для диагностики
        return


def save_debug_html(driver: webdriver.Chrome, config: YandexParserConfig) -> Path:
    debug_dir = Path(config.debug_dir)
    debug_dir.mkdir(parents=True, exist_ok=True)

    source_object_id = extract_source_object_id(config.url)
    path = debug_dir / f"yandex_{source_object_id}_debug.html"

    path.write_text(driver.page_source, encoding="utf-8")
    return path


def extract_reviews_from_page(
    driver: webdriver.Chrome,
    source_object_id: str,
    source_url: str,
    limit: int,
) -> list[dict[str, Any]]:
    cards = driver.find_elements(By.CSS_SELECTOR, ".business-review-view__info")

    reviews: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for card in cards:
        try:
            card_html = card.get_attribute("outerHTML")
        except WebDriverException:
            continue

        if not card_html:
            continue

        review = extract_review_from_card(
            card_html=card_html,
            source_object_id=source_object_id,
            source_url=source_url,
        )

        if review is None:
            continue

        review_id = str(review["review_id"])

        if review_id in seen_ids:
            continue

        seen_ids.add(review_id)
        reviews.append(review)

        if len(reviews) >= limit:
            break

    return reviews


def parse_yandex_reviews(config: YandexParserConfig) -> dict[str, Any]:
    """
    Основная функция Яндекс-парсера.

    Возвращает:
    {
        "meta": {...},
        "reviews": [...]
    }
    """
    source_object_id = extract_source_object_id(config.url)

    driver = create_driver(config)

    try:
        driver.get(config.url)
        time.sleep(3)

        close_popups(driver)
        wait_for_reviews(driver, config.wait_seconds)
        scroll_reviews(driver, config)

        if config.save_debug_html:
            debug_path = save_debug_html(driver, config)
            print(f"Debug HTML saved: {debug_path}")

        reviews = extract_reviews_from_page(
            driver=driver,
            source_object_id=source_object_id,
            source_url=config.url,
            limit=config.limit,
        )

    finally:
        driver.quit()

    result = {
        "meta": {
            "source": "yandex",
            "source_object_id": source_object_id,
            "source_url": config.url,
            "city": config.city,
            "object_type": config.object_type,
            "rows": len(reviews),
            "config": asdict(config),
        },
        "reviews": reviews,
    }

    return result


def save_raw_result(result: dict[str, Any], raw_dir: str | Path) -> Path:
    raw_dir = Path(raw_dir)
    raw_dir.mkdir(parents=True, exist_ok=True)

    source_object_id = result["meta"]["source_object_id"]
    path = raw_dir / f"yandex_{source_object_id}_reviews.json"

    with path.open("w", encoding="utf-8") as file:
        json.dump(result, file, ensure_ascii=False, indent=2)

    return path


def parse_and_save_yandex_reviews(config: YandexParserConfig) -> dict[str, Any]:
    result = parse_yandex_reviews(config)
    raw_path = save_raw_result(result, config.raw_dir)
    print(f"Raw Yandex reviews saved: {raw_path}")
    print(f"Parsed reviews: {len(result['reviews'])}")
    return result

class YandexLiveParser:

    def __init__(self, config: YandexParserConfig):
        self.config = config

    def parse(self) -> dict[str, Any]:
        return parse_and_save_yandex_reviews(self.config)

    def run(self) -> dict[str, Any]:
        return self.parse()

    def parse_reviews(self) -> dict[str, Any]:
        return self.parse()
# Совместимость с возможными импортами из pipeline.py
def run_yandex_parser(config: YandexParserConfig) -> dict[str, Any]:
    return parse_and_save_yandex_reviews(config)


def parse(config: YandexParserConfig) -> dict[str, Any]:
    return parse_and_save_yandex_reviews(config)