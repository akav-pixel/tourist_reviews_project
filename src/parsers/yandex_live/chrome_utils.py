from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from selenium import webdriver
from selenium.webdriver.chrome.options import Options


@dataclass(slots=True)
class ChromeConfig:
    headless: bool = True
    user_data_dir: str | None = None
    profile_directory: str | None = None
    window_width: int = 1440
    window_height: int = 1000
    page_load_timeout: int = 45


def build_chrome_options(config: ChromeConfig) -> Options:
    options = Options()
    if config.headless:
        options.add_argument("--headless=new")
    options.add_argument(f"--window-size={config.window_width},{config.window_height}")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--lang=ru-RU")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    if config.user_data_dir:
        options.add_argument(f"--user-data-dir={Path(config.user_data_dir).expanduser()}")
    if config.profile_directory:
        options.add_argument(f"--profile-directory={config.profile_directory}")

    return options


def create_chrome_driver(config: ChromeConfig) -> webdriver.Chrome:
    """Create Chrome driver using Selenium Manager (Selenium 4.6+)."""
    driver = webdriver.Chrome(options=build_chrome_options(config))
    driver.set_page_load_timeout(config.page_load_timeout)
    return driver
