# HN Article Enricher

A FastAPI service that scrapes Hacker News front page, enriches each article with OpenAI, and exposes the results via a REST API.

## Stack

- **FastAPI** — async REST API
- **SQLAlchemy (async) + aiosqlite** — SQLite persistence
- **httpx + BeautifulSoup** — scraping (static HTML, no JS rendering needed)
- **OpenAI `gpt-4o-mini`** — structured enrichment (category, tags, summary, sentiment)
- **tenacity** — retry with exponential backoff
- **Pydantic v2** — config and schema validation

## Quick Start

```bash
# 1. Install dependencies
pip install -r requirements.txt

# 2. Configure .env (set OPENAI_API_KEY)
cp .env.example .env

# 3. Run migrations
alembic upgrade head

# 4. Start server
uvicorn app.main:app --reload
```

**📖 For detailed setup instructions, see [QUICKSTART.md](./docs/QUICKSTART.md)**

The API will be available at `http://localhost:8000`.  
Interactive docs: `http://localhost:8000/docs`

## Running tests

```bash
python -m pytest tests/ -v

# With coverage report
python -m pytest tests/ --cov=app --cov-report=html
```

Tests use an in-memory SQLite database and do not call the real OpenAI API.

## Usage

### Authentication (Optional)

Protected endpoints require an API key if configured in `.env`:

```bash
# Set in .env
API_KEY=your-secret-key-here
```

Then include the key in requests:

```bash
curl -H "X-API-Key: your-secret-key-here" ...
```

### Run the pipeline (scrape + enrich)

The pipeline now runs in background and returns immediately:

```bash
curl -X POST http://localhost:8000/api/v1/pipeline/run \
  -H "X-API-Key: your-secret-key-here"
```

Response:

```json
{
  "job_id": 1,
  "status": "pending",
  "message": "Pipeline job 1 started in background"
}
```

### Check job status

```bash
curl http://localhost:8000/api/v1/pipeline/jobs/1
```

Response:

```json
{
  "id": 1,
  "status": "completed",
  "created_at": "2024-01-01T12:00:00",
  "started_at": "2024-01-01T12:00:01",
  "completed_at": "2024-01-01T12:00:15",
  "scraped": 30,
  "new_items": 25,
  "enriched": 24,
  "failed": 1,
  "error_message": null
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

# List recent jobs
curl http://localhost:8000/api/v1/pipeline/jobs

# Available categories
curl http://localhost:8000/api/v1/articles/categories

# Test LLM connection (requires API key)
curl http://localhost:8000/api/v1/pipeline/test-llm \
  -H "X-API-Key: your-secret-key-here"

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
├── models.py            # SQLAlchemy ORM models (Article)
├── job_models.py        # Job tracking models (PipelineJob)
├── tag_models.py        # Tag models with many-to-many relationship
├── schemas.py           # Pydantic request/response schemas
├── middleware.py        # Authentication and rate limiting
├── background_jobs.py   # Async pipeline execution
├── scraper/
│   └── hn_scraper.py    # HN front page scraper
├── enrichment/
│   └── llm_enricher.py  # OpenAI enrichment with retry + validation
└── routers/
    ├── articles.py      # CRUD + filter endpoints
    └── pipeline.py      # Background job management endpoints

alembic/
├── versions/            # Database migrations
│   └── 001_initial_schema.py
├── env.py              # Alembic async environment
└── script.py.mako      # Migration template

tests/
├── test_api.py                    # API endpoint tests
├── test_schemas.py                # Schema validation tests
├── test_scraper.py                # Scraper tests
├── test_pipeline_integration.py   # Full pipeline flow tests
└── test_auth_and_rate_limit.py    # Security tests
```

## Documentation

- [IMPROVEMENTS.md](./IMPROVEMENTS.md) - Detailed documentation of all improvements
- [RATIONALE.md](./RATIONALE.md) - Engineering decisions and trade-offs
- [AGENT_WORKFLOW.md](./AGENT_WORKFLOW.md) - AI agent development workflow

## What's New

This project has been significantly improved based on technical review feedback:

✅ **Background Jobs** - Pipeline runs asynchronously, no more blocking requests  
✅ **Authentication** - API key protection for cost-generating endpoints  
✅ **Rate Limiting** - Configurable request limits per client  
✅ **Concurrency Control** - Only one pipeline job runs at a time  
✅ **Database Migrations** - Alembic for schema evolution  
✅ **Structured Logging** - Better observability with contextual logs  
✅ **Improved Tag Model** - Dedicated table with indexes for efficient queries  
✅ **Comprehensive Tests** - Integration tests covering failures and edge cases

See [IMPROVEMENTS.md](./IMPROVEMENTS.md) for complete details.
