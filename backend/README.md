# Campaign Data Hub — Backend

FastAPI + SQLAlchemy + Alembic + PostgreSQL.

## Prerequisites

- Python 3.12+
- PostgreSQL 16 (repo-root `docker compose up -d db`)

## Setup

```bash
cd backend
python3 -m venv .venv
source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

## Run

```bash
# from repo root
docker compose up -d db

# from backend/
alembic upgrade head
uvicorn app.main:app --reload --port 8000
```

- Health: `GET http://localhost:8000/api/v1/health`
- OpenAPI: http://localhost:8000/docs

## API

- `GET /api/v1/metrics`
- `GET /api/v1/deliveries`
- `GET /api/v1/deliveries/{id}`
- `GET /api/v1/deliveries/{id}/quality-report`
- `POST /api/v1/ingestions`
- `GET /api/v1/ingestions/{id}`

## Ingest

```bash
python -m app.ingestion.cli --data-dir ../assessment/data
```

See the root `README.md` for normalization rules, quality checks, and design notes.

## Tests

```bash
pytest
```
