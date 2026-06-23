from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
    )

    database_url: str = "sqlite+aiosqlite:///./hn_articles.db"

    openai_api_key: str
    openai_model: str = "gpt-4o-mini"

    scraper_timeout: int = 30
    scraper_max_retries: int = 3
    
    selenium_headless: bool = True
    selenium_wait_timeout: int = 10
    selenium_page_load_timeout: int = 30
    selenium_scroll_pause_time: float = 2.0
    selenium_max_scrolls: int = 10

    llm_max_tokens: int = 400
    llm_title_max_chars: int = 200
    llm_concurrency: int = 5

    api_key: str = ""
    rate_limit_per_minute: int = 10
    
    environment: str = "development"
    log_level: str = "INFO"


settings = Settings()
