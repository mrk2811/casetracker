"""
Headless browser engine for court website scraping.

Provides a Selenium-based fallback when the primary httpx scraper
is blocked by Cloudflare or other JavaScript-based challenges.
Runs Chrome in headless mode with stealth-oriented options.
"""

import asyncio
import logging
import random
import time
from typing import Optional

from bs4 import BeautifulSoup
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import Select, WebDriverWait

from app.scraper.engine import ScrapeResult, USER_AGENTS

logger = logging.getLogger(__name__)

# How long to wait for page elements (seconds)
DEFAULT_PAGE_TIMEOUT = 30


def _build_chrome_options() -> Options:
    """Build Chrome options configured for headless stealth scraping."""
    options = Options()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_argument("--window-size=1920,1080")

    ua = random.choice(USER_AGENTS)
    options.add_argument(f"--user-agent={ua}")

    # Reduce automation fingerprint
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option("useAutomationExtension", False)

    return options


def _create_driver() -> webdriver.Chrome:
    """Create a headless Chrome WebDriver instance."""
    options = _build_chrome_options()
    service = Service()
    driver = webdriver.Chrome(service=service, options=options)
    # Remove webdriver flag to reduce detection
    driver.execute_cdp_cmd(
        "Page.addScriptToEvaluateOnNewDocument",
        {
            "source": """
                Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
            """
        },
    )
    driver.set_page_load_timeout(DEFAULT_PAGE_TIMEOUT)
    return driver


class BrowserEngine:
    """
    Selenium-based headless browser engine for bypassing JS challenges.

    Used as a fallback when the primary httpx-based ScraperEngine fails
    due to Cloudflare or similar JavaScript-based protections.
    """

    def __init__(self) -> None:
        self._driver: Optional[webdriver.Chrome] = None

    def _get_driver(self) -> webdriver.Chrome:
        """Get or create the Chrome WebDriver."""
        if self._driver is None:
            self._driver = _create_driver()
        return self._driver

    async def get(self, url: str) -> ScrapeResult:
        """Navigate to a URL and return the page HTML."""
        start_time = time.monotonic()
        try:
            driver = self._get_driver()
            html = await asyncio.to_thread(self._sync_get, driver, url)
            elapsed_ms = (time.monotonic() - start_time) * 1000

            soup = BeautifulSoup(html, "lxml")
            return ScrapeResult(
                success=True,
                html=html,
                soup=soup,
                status_code=200,
                response_time_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error("Browser GET failed for %s: %s", url, exc)
            return ScrapeResult(
                success=False,
                error_message=f"Browser error: {exc}",
                response_time_ms=elapsed_ms,
            )

    async def post_form(
        self,
        page_url: str,
        form_fields: dict[str, str],
        submit_selector: Optional[str] = None,
        select_fields: Optional[dict[str, str]] = None,
    ) -> ScrapeResult:
        """
        Navigate to a page, fill in a form, submit it, and return the result HTML.

        Args:
            page_url: URL of the page containing the form.
            form_fields: Mapping of input name -> value for text inputs.
            submit_selector: CSS selector for the submit button.
                             If None, the form is submitted via the first
                             ``<input type="submit">`` found.
            select_fields: Mapping of select name -> visible text for dropdowns.
        """
        start_time = time.monotonic()
        try:
            driver = self._get_driver()
            html = await asyncio.to_thread(
                self._sync_post_form,
                driver,
                page_url,
                form_fields,
                submit_selector,
                select_fields,
            )
            elapsed_ms = (time.monotonic() - start_time) * 1000

            soup = BeautifulSoup(html, "lxml")
            return ScrapeResult(
                success=True,
                html=html,
                soup=soup,
                status_code=200,
                response_time_ms=elapsed_ms,
            )
        except Exception as exc:
            elapsed_ms = (time.monotonic() - start_time) * 1000
            logger.error("Browser POST form failed for %s: %s", page_url, exc)
            return ScrapeResult(
                success=False,
                error_message=f"Browser error: {exc}",
                response_time_ms=elapsed_ms,
            )

    # ------------------------------------------------------------------
    # Synchronous helpers (run via asyncio.to_thread)
    # ------------------------------------------------------------------

    @staticmethod
    def _sync_get(driver: webdriver.Chrome, url: str) -> str:
        driver.get(url)
        # Wait for body to be present
        WebDriverWait(driver, DEFAULT_PAGE_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )
        # Small random delay to mimic human
        time.sleep(random.uniform(1.0, 2.5))
        return driver.page_source

    @staticmethod
    def _sync_post_form(
        driver: webdriver.Chrome,
        page_url: str,
        form_fields: dict[str, str],
        submit_selector: Optional[str],
        select_fields: Optional[dict[str, str]],
    ) -> str:
        # Navigate to the form page
        driver.get(page_url)
        WebDriverWait(driver, DEFAULT_PAGE_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        # Small delay before interacting
        time.sleep(random.uniform(0.5, 1.5))

        # Fill select/dropdown fields first
        if select_fields:
            for name, value in select_fields.items():
                try:
                    el = driver.find_element(By.NAME, name)
                    select = Select(el)
                    select.select_by_value(value)
                    time.sleep(random.uniform(0.2, 0.5))
                except Exception as exc:
                    logger.warning(
                        "Browser: could not set select field %s=%s: %s",
                        name,
                        value,
                        exc,
                    )

        # Fill text input fields
        for name, value in form_fields.items():
            try:
                el = driver.find_element(By.NAME, name)
                el.clear()
                # Type character-by-character with small delays for realism
                for char in value:
                    el.send_keys(char)
                    time.sleep(random.uniform(0.02, 0.08))
                time.sleep(random.uniform(0.2, 0.5))
            except Exception as exc:
                logger.warning(
                    "Browser: could not fill field %s: %s", name, exc
                )

        # Submit the form
        time.sleep(random.uniform(0.5, 1.0))
        if submit_selector:
            btn = driver.find_element(By.CSS_SELECTOR, submit_selector)
            btn.click()
        else:
            try:
                btn = driver.find_element(
                    By.CSS_SELECTOR, "input[type='submit']"
                )
                btn.click()
            except Exception:
                # Fallback: submit the first form on the page
                form = driver.find_element(By.TAG_NAME, "form")
                form.submit()

        # Wait for results to load
        time.sleep(random.uniform(2.0, 4.0))
        WebDriverWait(driver, DEFAULT_PAGE_TIMEOUT).until(
            EC.presence_of_element_located((By.TAG_NAME, "body"))
        )

        return driver.page_source

    def close(self) -> None:
        """Quit the browser and release resources."""
        if self._driver is not None:
            try:
                self._driver.quit()
            except Exception:
                pass
            self._driver = None

    def __del__(self) -> None:
        self.close()
