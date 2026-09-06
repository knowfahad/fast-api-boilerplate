# Runbook

## 1. Start the server from scratch (after cleanup)

```bash
# 0. Clean slate (optional)
rm -rf .venv .pytest_cache .ruff_cache && find . -name __pycache__ -prune -exec rm -rf {} +

# 1. Prereqs: Python 3.12 + uv   (brew install uv)

# 2. Install deps into .venv from uv.lock
uv sync

# 3. Config (optional; every var has a default)
cp .env.example .env

# 4a. Dev (auto-reload)
uv run uvicorn app.main:app --reload            # http://localhost:8000/docs

# 4b. Prod-style (env-driven HOST/PORT/WORKERS/LOG_LEVEL)
uv run python -m app.main
PORT=8080 WORKERS=4 uv run python -m app.main

# 5. Smoke test
curl -s localhost:8000/openapi.json -o /dev/null -w '%{http_code}\n'
curl -s -X POST localhost:8000/greetings -H 'Content-Type: application/json' -d '{"name":"world"}'

# 6. Quality gates
uv run pytest
uv run ruff check . && uv run ruff format --check .

# 7. Container
docker build -t fahad:local . && docker run --rm -p 8000:8000 fahad:local
# or
docker compose up --build
```

## 2. Add a domain feature (`tasks`)

Mirrors the existing `app/feature/` layout: one self-contained module per domain.
`service.py` holds async domain logic, `router.py` is the HTTP adapter + Pydantic
models. Wire it with one line in `app/main.py`.

### 1. `app/tasks/__init__.py`

Empty file (marks the package).

### 2. `app/tasks/service.py` — domain + async logic (in-memory store)

```python
from dataclasses import dataclass
from itertools import count


@dataclass
class Task:
    id: int
    title: str
    done: bool = False


_tasks: dict[int, Task] = {}  # per-process; swap for a DB later (see docs/db.README.md)
_ids = count(1)


async def create_task(title: str) -> Task:
    task = Task(id=next(_ids), title=title)
    _tasks[task.id] = task
    return task


async def list_tasks() -> list[Task]:
    return list(_tasks.values())


async def get_task(task_id: int) -> Task | None:
    return _tasks.get(task_id)
```

### 3. `app/tasks/router.py` — models + endpoints

```python
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel, ConfigDict, Field

from app.tasks import service

router = APIRouter(prefix="/tasks", tags=["tasks"])


class TaskCreate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)

    title: str = Field(min_length=1, max_length=200, examples=["write runbook"])


class TaskResponse(BaseModel):
    id: int
    title: str
    done: bool


@router.post("", response_model=TaskResponse, status_code=201, summary="Create a task")
async def create_task(payload: TaskCreate) -> TaskResponse:
    task = await service.create_task(payload.title)
    return TaskResponse(id=task.id, title=task.title, done=task.done)


@router.get("", response_model=list[TaskResponse], summary="List tasks")
async def list_tasks() -> list[TaskResponse]:
    return [TaskResponse(id=t.id, title=t.title, done=t.done) for t in await service.list_tasks()]


@router.get("/{task_id}", response_model=TaskResponse, summary="Get a task")
async def get_task(task_id: int) -> TaskResponse:
    task = await service.get_task(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return TaskResponse(id=task.id, title=task.title, done=task.done)
```

### 4. Register it in `app/main.py` (2 lines)

```python
from app.tasks.router import router as tasks_router  # with the other imports

# ...inside create_app():
app.include_router(tasks_router)
```

### 5. `tests/test_tasks.py`

```python
from fastapi.testclient import TestClient


def test_create_get_list_task(client: TestClient) -> None:
    created = client.post("/tasks", json={"title": "write runbook"})
    assert created.status_code == 201
    task = created.json()
    assert task["title"] == "write runbook" and task["done"] is False
    assert client.get(f"/tasks/{task['id']}").json() == task
    assert len(client.get("/tasks").json()) >= 1


def test_missing_task_404(client: TestClient) -> None:
    assert client.get("/tasks/999999").status_code == 404
```

### 6. Verify

```bash
uv run ruff check . && uv run pytest
uv run python -m app.main          # then curl POST/GET /tasks; /docs shows the "tasks" group
```

**Scaling the domain later (only when needed):** split the Pydantic models into
`schemas.py`, put persistent entities in `models.py`, keep logic in `service.py`,
and add a database per `docs/db.README.md`. The in-memory store is not shared across
`WORKERS>1` or replicas — move to a DB before that matters.
