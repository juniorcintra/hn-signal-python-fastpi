import logging
from bs4 import BeautifulSoup

from .selenium_scraper import SeleniumScrollScraper
from ..config import settings

logger = logging.getLogger(__name__)


class ExampleDynamicScraper(SeleniumScrollScraper):

    def __init__(self):
        super().__init__(
            headless=settings.selenium_headless,
            wait_timeout=settings.selenium_wait_timeout,
            page_load_timeout=settings.selenium_page_load_timeout,
            scroll_pause_time=settings.selenium_scroll_pause_time,
            max_scrolls=settings.selenium_max_scrolls,
        )

    def parse(self, html: str) -> list[dict]:
        soup = BeautifulSoup(html, "lxml")
        articles = []

        article_elements = soup.select(".article-item")

        for element in article_elements:
            try:
                title_el = element.select_one(".article-title")
                link_el = element.select_one(".article-link")
                date_el = element.select_one(".article-date")

                if not title_el or not link_el:
                    continue

                articles.append(
                    {
                        "title": title_el.get_text(strip=True),
                        "url": link_el.get("href"),
                        "published_at": date_el.get_text(strip=True) if date_el else None,
                    }
                )

            except Exception as exc:
                logger.warning(f"Skipping article due to parse error: {exc}")
                continue

        return articles


async def scrape_dynamic_site(url: str) -> list[dict]:
    scraper = ExampleDynamicScraper()
    logger.info(f"Scraping dynamic site: {url}")
    articles = await scraper.scrape(url)
    logger.info(f"Parsed {len(articles)} articles from {url}")
    return articles
