# Adding a database

The app ships without a database on purpose. When a feature actually needs one,
add async SQLAlchemy + PostgreSQL in a few steps. Everything stays `async`.

## 1. Add dependencies

```bash
uv add "sqlalchemy[asyncio]>=2.0" "psycopg[binary]>=3.2"
# optional, only if you want migrations:
uv add "alembic>=1.14"
```

## 2. Add the connection setting

In `app/settings.py`, add one field:

```python
database_url: str = "postgresql+psycopg://postgres:postgres@localhost:5432/fahad"
```

and document `DATABASE_URL` in `.env.example` / the README table.

## 3. Create `app/db.py`

```python
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase

from app.settings import get_settings


class Base(DeclarativeBase):
    pass


engine = create_async_engine(get_settings().database_url, pool_pre_ping=True)
SessionFactory = async_sessionmaker(engine, expire_on_commit=False)


async def get_session() -> AsyncIterator[AsyncSession]:
    async with SessionFactory() as session:
        yield session
```

## 4. Define a model + use it in a feature

```python
# app/feature/models.py
from sqlalchemy.orm import Mapped, mapped_column

from app.db import Base


class Item(Base):
    __tablename__ = "items"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str]
```

```python
# app/feature/service.py
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.feature.models import Item


async def list_items(session: AsyncSession) -> list[Item]:
    result = await session.execute(select(Item))
    return list(result.scalars())
```

```python
# app/feature/router.py — inject the session
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.db import get_session

SessionDep = Annotated[AsyncSession, Depends(get_session)]


@router.get("/items")
async def get_items(session: SessionDep):
    return await list_items(session)
```

## 5. Run Postgres locally (Compose)

Add a `db` service to `compose.yaml` and point the API at it:

```yaml
services:
  api:
    # ...existing config...
    environment:
      DATABASE_URL: postgresql+psycopg://postgres:postgres@db:5432/fahad
    depends_on:
      - db

  db:
    image: postgres:17-alpine
    environment:
      POSTGRES_USER: postgres
      POSTGRES_PASSWORD: postgres
      POSTGRES_DB: fahad
    ports:
      - "5432:5432"
    volumes:
      - postgres-data:/var/lib/postgresql/data

volumes:
  postgres-data:
```

## 6. Migrations (optional, with Alembic)

```bash
uv run alembic init -t async alembic
```

Then in `alembic/env.py` use the app's URL and metadata:

```python
from app.db import Base
from app.settings import get_settings

target_metadata = Base.metadata
config.set_main_option("sqlalchemy.url", get_settings().database_url)
```

Import your models in `env.py` (so autogenerate sees them), then:

```bash
uv run alembic revision --autogenerate -m "create items"
uv run alembic upgrade head
```

Run migrations as a one-off (locally or a Kubernetes Job) — never from the app
process at startup. Keep each migration backward compatible with the running
image so a rollback never needs a `downgrade`.
