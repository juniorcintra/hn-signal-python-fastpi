import asyncio
import logging
from typing import Optional

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait
from webdriver_manager.chrome import ChromeDriverManager

from ..config import settings
from .base import BaseScraper

logger = logging.getLogger(__name__)


class SeleniumScraper(BaseScraper):

    def __init__(
        self,
        headless: bool = True,
        wait_timeout: int = 10,
        page_load_timeout: int = 30,
    ):
        self.headless = headless
        self.wait_timeout = wait_timeout
        self.page_load_timeout = page_load_timeout

    def _create_driver(self) -> webdriver.Chrome:
        chrome_options = Options()

        if self.headless:
            chrome_options.add_argument("--headless=new")

        chrome_options.add_argument("--no-sandbox")
        chrome_options.add_argument("--disable-dev-shm-usage")
        chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        chrome_options.add_argument(
            "user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        )

        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        driver.set_page_load_timeout(self.page_load_timeout)

        return driver

    async def fetch(self, url: str) -> str:
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, self._fetch_sync, url)

    def _fetch_sync(self, url: str) -> str:
        driver = None
        try:
            logger.info(f"Fetching URL with Selenium: {url}")
            driver = self._create_driver()
            driver.get(url)

            WebDriverWait(driver, self.wait_timeout).until(
                EC.presence_of_element_located((By.TAG_NAME, "body"))
            )

            self._handle_dynamic_content(driver)

            html = driver.page_source
            logger.info(f"Successfully fetched {len(html)} bytes from {url}")
            return html

        except Exception as exc:
            logger.error(f"Selenium fetch failed for {url}: {exc}")
            raise

        finally:
            if driver:
                driver.quit()

    def _handle_dynamic_content(self, driver: webdriver.Chrome) -> None:
        pass

    def parse(self, html: str) -> list[dict]:
        raise NotImplementedError(
            "SeleniumScraper.parse() must be implemented by subclass"
        )


class SeleniumScrollScraper(SeleniumScraper):

    def __init__(
        self,
        headless: bool = True,
        wait_timeout: int = 10,
        page_load_timeout: int = 30,
        scroll_pause_time: float = 2.0,
        max_scrolls: int = 10,
    ):
        super().__init__(headless, wait_timeout, page_load_timeout)
        self.scroll_pause_time = scroll_pause_time
        self.max_scrolls = max_scrolls

    def _handle_dynamic_content(self, driver: webdriver.Chrome) -> None:
        logger.info("Handling infinite scroll...")

        last_height = driver.execute_script("return document.body.scrollHeight")
        scrolls = 0

        while scrolls < self.max_scrolls:
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")

            import time
            time.sleep(self.scroll_pause_time)

            new_height = driver.execute_script("return document.body.scrollHeight")

            if new_height == last_height:
                logger.info(f"Reached end of page after {scrolls} scrolls")
                break

            last_height = new_height
            scrolls += 1

        logger.info(f"Completed {scrolls} scrolls")
