# HN Article Enricher

A FastAPI service that scrapes Hacker News front page, enriches each article with OpenAI, and exposes the results via a REST API.

## Stack

- **FastAPI** — async REST API
- **SQLAlchemy (async) + aiosqlite** — SQLite persistence
- **httpx + BeautifulSoup** — scraping (static HTML, no JS rendering needed)
- **OpenAI `gpt-4o-mini`** — structured enrichment (category, tags, summary, sentiment)
- **tenacity** — retry with exponential backoff
- **Pydantic v2** — config and schema validation

## Setup

```bash
# 1. Create and activate a virtual environment
python -m venv .venv
.venv\Scripts\activate        # Windows
# source .venv/bin/activate   # Linux/macOS

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure environment
cp .env.example .env
# Edit .env and set your OPENAI_API_KEY

# 4. Run the server
uvicorn app.main:app --reload
```

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

## Running tests

```bash
python -m pytest tests/ -v
```

Tests use an in-memory SQLite database and do not call the real OpenAI API.

## Usage

### Run the pipeline (scrape + enrich)

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run
```

Response:

```json
{
  "scraped": 30,
  "new_items": 25,
  "enriched": 24,
  "failed": 1,
  "message": "Pipeline completed successfully"
}
```

### List articles

```bash
# All articles, paginated
curl "http://localhost:8000/api/v1/articles?page=1&page_size=10"

# Filter by category
curl "http://localhost:8000/api/v1/articles?category=technology"

# Filter by tag
curl "http://localhost:8000/api/v1/articles?tag=python"

# Only enriched items
curl "http://localhost:8000/api/v1/articles?enrichment_status=completed"
```

### Other endpoints

```bash
# Healthcheck
curl http://localhost:8000/health

# Pipeline stats
curl http://localhost:8000/api/v1/pipeline/stats

# Available categories
curl http://localhost:8000/api/v1/articles/categories

# Retry failed enrichments
curl -X POST http://localhost:8000/api/v1/pipeline/retry

# Get a single article
curl http://localhost:8000/api/v1/articles/1
```

## Project Structure

```
app/
├── main.py              # FastAPI app, lifespan, global error handler
├── config.py            # Pydantic-settings configuration
├── database.py          # Async engine, session factory, init_db
├── enums.py             # Shared enums (EnrichmentStatus)
├── models.py            # SQLAlchemy ORM models
├── schemas.py           # Pydantic request/response schemas
├── scraper/
│   └── hn_scraper.py    # HN front page scraper
├── enrichment/
│   └── llm_enricher.py  # OpenAI enrichment with retry + validation
└── routers/
    ├── articles.py      # CRUD + filter endpoints
    └── pipeline.py      # Pipeline trigger endpoints
```

See [RATIONALE.md](./RATIONALE.md) for a full explanation of engineering decisions.  
See [AGENT_WORKFLOW.md](./AGENT_WORKFLOW.md) for how the AI agent was used in development.
