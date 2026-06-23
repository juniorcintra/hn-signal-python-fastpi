from abc import ABC, abstractmethod
from typing import Optional


class BaseScraper(ABC):
    @abstractmethod
    async def fetch(self, url: str) -> str:
        pass

    @abstractmethod
    def parse(self, html: str) -> list[dict]:
        pass

    async def scrape(self, url: str) -> list[dict]:
        html = await self.fetch(url)
        return self.parse(html)
