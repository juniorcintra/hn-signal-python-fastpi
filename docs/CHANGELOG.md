# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.0.0] - 2024-01-01

### Added

#### Background Jobs System
- **Pipeline jobs now run asynchronously** - No more blocking HTTP requests
- New `pipeline_jobs` table to track execution history
- `POST /api/v1/pipeline/run` returns immediately with job ID
- `GET /api/v1/pipeline/jobs/{job_id}` to check job status
- `GET /api/v1/pipeline/jobs` to list recent jobs
- Job status tracking: pending → running → completed/failed

#### Security & Rate Limiting
- **API key authentication** for cost-generating endpoints
- Configurable via `API_KEY` environment variable
- Rate limiting (10 req/min default, configurable)
- Protected endpoints:
  - `POST /api/v1/pipeline/run`
  - `GET /api/v1/pipeline/test-llm`
- In-memory rate limiter with per-client tracking

#### Database Migrations
- **Alembic integration** for schema versioning
- Initial migration `001_initial_schema.py`
- Support for async migrations
- Commands: `alembic upgrade head`, `alembic revision --autogenerate`

#### Improved Logging
- Structured logs with file/line information
- Configurable log level via `LOG_LEVEL` env var
- Environment-aware logging (`ENVIRONMENT` setting)
- Better context in pipeline execution logs

#### Tag Modeling
- New `tags` table with indexed name column
- Many-to-many relationship via `article_tags` table
- Backward compatible with JSON `tags` column
- Eager loading of tag relationships

#### Testing
- **Integration tests** for complete pipeline flow
- Tests for partial enrichment failures
- Idempotency tests (no re-enrichment)
- Scraper failure scenarios
- Concurrent pipeline prevention tests
- Authentication and rate limiting tests
- Coverage increased from ~60% to ~85%

#### Documentation
- `IMPROVEMENTS.md` - Detailed improvement documentation
- `MIGRATION_GUIDE.md` - Step-by-step migration guide
- `CHANGELOG.md` - Version history
- Updated README with new features

### Changed

#### Breaking Changes
- `POST /api/v1/pipeline/run` response format changed:
  - **Before:** `{"scraped": 30, "new_items": 25, "enriched": 24, "failed": 1, "message": "..."}`
  - **After:** `{"job_id": 1, "status": "pending", "message": "Pipeline job 1 started in background"}`
- Pipeline execution is now asynchronous (use job status endpoint to poll)

#### Non-Breaking Changes
- Improved error messages with more context
- Better handling of concurrent pipeline requests (HTTP 409)
- Enhanced health check endpoint
- More detailed pipeline stats

### Removed

- `POST /api/v1/pipeline/retry` endpoint (use manual status update + new job)

### Fixed

- Race conditions from concurrent pipeline executions
- Missing indexes on frequently queried columns
- Inconsistent error handling in pipeline
- Memory leaks in long-running processes

### Security

- API key authentication prevents unauthorized LLM usage
- Rate limiting prevents abuse and cost overruns
- Input validation on all endpoints
- No sensitive data in logs

## [1.0.0] - 2023-12-01

### Added
- Initial release
- HN scraper with BeautifulSoup
- OpenAI enrichment with GPT-4o-mini
- SQLite persistence with async SQLAlchemy
- REST API with FastAPI
- Article CRUD endpoints
- Category and tag filtering
- Synchronous pipeline execution
- Basic error handling
- Unit tests for core functionality

---

## Migration Notes

### Upgrading from 1.0.0 to 2.0.0

**Required Steps:**
1. Backup database: `cp hn_articles.db hn_articles.db.backup`
2. Install new dependencies: `pip install -r requirements.txt`
3. Run migrations: `alembic upgrade head`
4. Update `.env` with new variables (see `.env.example`)
5. Update API clients to handle async job responses

**Optional Steps:**
- Configure API key for authentication
- Adjust rate limiting settings
- Update log level for production

See [MIGRATION_GUIDE.md](./MIGRATION_GUIDE.md) for detailed instructions.

---

## Versioning Strategy

- **Major version (X.0.0):** Breaking API changes
- **Minor version (0.X.0):** New features, backward compatible
- **Patch version (0.0.X):** Bug fixes, no API changes

## Roadmap

### v2.1.0 (Planned)
- [ ] Webhook notifications for job completion
- [ ] Tag migration script (JSON → relational)
- [ ] Cursor-based pagination
- [ ] Redis-backed rate limiting
- [ ] Prometheus metrics endpoint

### v2.2.0 (Planned)
- [ ] Celery/RQ worker integration
- [ ] Multi-source scraping (Reddit, Lobsters)
- [ ] Custom enrichment prompts
- [ ] Bulk article import/export

### v3.0.0 (Future)
- [ ] Multi-tenancy support
- [ ] GraphQL API
- [ ] Real-time updates via WebSocket
- [ ] Advanced search with Elasticsearch
