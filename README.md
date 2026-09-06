# Minimal fast-api boilerplate 

### I carefully AI-coded this for my own projects but if someone wants to use it, feel free! :) 

Minimal async FastAPI service using Python 3.12, uv, Pydantic v2, and Uvicorn. Includes a greeting endpoint demonstrating routing, async service logic, and request/response models. No database, authentication, or CI—just enough to build quickly and deploy to Kubernetes.

You can extend the db quite easily, refer to the docs. Also provided the kubernetes yamls for convenience. 

## Requirements

- Python 3.12
- [uv](https://docs.astral.sh/uv/) (`brew install uv`)
- Docker (for the image / Compose)

## Install

```bash
uv sync
cp .env.example .env   # optional; every setting has a default
```

`uv sync` creates `.venv` from `uv.lock`. Prefix commands with `uv run`.

## Local development

```bash
uv run uvicorn app.main:app --reload        # http://localhost:8000/docs
```

To run it exactly as the container does (uvicorn started from `Settings`):

```bash
uv run python -m app.main                     # binds HOST:PORT from env
PORT=8080 uv run python -m app.main
WORKERS=4 uv run python -m app.main           # multiple uvicorn workers
```

Try it:

```bash
curl -X POST http://localhost:8000/greetings \
  -H 'Content-Type: application/json' -d '{"name":"world"}'
# {"message":"Hello, world! Welcome to fahad.","app_name":"fahad"}
```

## Tests

```bash
uv run pytest
```

The `client` fixture sets `APP_NAME`, clears the `get_settings` cache and calls
`create_app()`, so tests need no `.env` file.

## Docker

```bash
docker build -t fahad:local .
docker run --rm -p 8000:8000 fahad:local
PORT=8080 docker run --rm -e PORT=8080 -p 8080:8080 fahad:local
```

The image is slim, multi-stage, and runs as a non-root user (uid 1001). It binds
`0.0.0.0` and reads the port from `PORT`.

## Docker Compose

```bash
docker compose up --build              # http://localhost:8000/docs
PORT=8080 docker compose up --build
docker compose down
```

Compose runs the API only (the app has no database). Add a service later if you
need one.

## Configuration

All settings are environment variables (read from the environment first, then
`.env`; unknown keys are ignored). Invalid values fail fast at startup.

| Variable | Default | Purpose |
| --- | --- | --- |
| `APP_NAME` | `fahad` | OpenAPI title, used by the greeting feature |
| `HOST` | `0.0.0.0` | uvicorn bind address |
| `PORT` | `8000` | uvicorn bind port |
| `WORKERS` | `1` | uvicorn worker processes |
| `LOG_LEVEL` | `info` | uvicorn log level |

## Structure

```
app/settings.py         Typed Settings from env vars, cached via get_settings()
app/main.py             create_app() factory, `app`, and the uvicorn entrypoint (python -m app.main)
app/feature/service.py  Async business logic
app/feature/router.py   APIRouter + Pydantic request/response models
app/health/router.py    Liveness/readiness endpoints (/health/live, /health/ready)
tests/                  pytest + FastAPI TestClient
deployment/             Kubernetes manifests (ConfigMap, Deployment, Service, Ingress)
docs/                   Guides: db.README.md, deployment.README.md
RUNBOOK.md              Start-from-scratch + add-a-feature runbook
```

Add a feature by creating another folder under `app/` with its own `router.py`
(and `service.py`) and one `include_router(...)` call in `app/main.py`.

## Guides

- [`docs/db.README.md`](docs/db.README.md) — add an async PostgreSQL database when a feature needs one.
- [`docs/deployment.README.md`](docs/deployment.README.md) — deploy to EKS (Deployment, Service, ALB Ingress).
