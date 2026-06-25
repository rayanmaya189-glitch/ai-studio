"""Database engine and session management (SQLAlchemy 2.0).

Two schema paths coexist:

* **Zero-config / dev / tests** — ``init_db()`` calls ``Base.metadata.create_all``
  on startup (plus the legacy idempotent column adds below). This keeps a fresh
  SQLite clone runnable with no migration step.
* **Production (Postgres)** — run ``alembic upgrade head`` (see ``alembic/``).
  ``create_all`` is a no-op once the schema exists, so the two are compatible;
  Alembic is the source of truth for schema evolution going forward.
"""

from __future__ import annotations

from collections.abc import Iterator

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from app.config import settings


class Base(DeclarativeBase):
    pass


# SQLite needs check_same_thread disabled for use across FastAPI threads.
connect_args = {"check_same_thread": False} if settings.database_url.startswith("sqlite") else {}
engine = create_engine(settings.database_url, connect_args=connect_args, future=True)
SessionLocal = sessionmaker(bind=engine, autoflush=False, expire_on_commit=False)


# Columns added after a table's first release. ``create_all`` creates missing
# tables but never alters existing ones, and there's no Alembic yet, so we add
# these idempotently on startup to keep older dev databases working. Each entry
# is (table, column, DDL type + default) and is only applied if absent.
_ADDED_COLUMNS: tuple[tuple[str, str, str], ...] = (
    ("agents", "project_id", "VARCHAR(32)"),
    ("agents", "kind", "VARCHAR(16) DEFAULT 'pipeline'"),
    ("agents", "description", "TEXT DEFAULT ''"),
    ("agents", "system_prompt", "TEXT DEFAULT ''"),
    # Newer models added columns after the initial "create_all" dev schema.
    # create_all never alters existing tables, so add additive columns idempotently.
    ("llm_provider_configs", "enabled", "INTEGER DEFAULT 0"),
    ("conversations", "session_id", "VARCHAR(32) DEFAULT NULL"),
)


def _apply_additive_migrations() -> None:
    inspector = inspect(engine)
    existing_tables = set(inspector.get_table_names())
    with engine.begin() as conn:
        for table, column, ddl in _ADDED_COLUMNS:
            if table not in existing_tables:
                continue  # create_all will build it fresh with all columns.
            cols = {c["name"] for c in inspector.get_columns(table)}
            if column in cols:
                continue
            conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {column} {ddl}"))


def init_db() -> None:
    # Import models so they register on Base.metadata before create_all.
    from app import models  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _apply_additive_migrations()


def get_db() -> Iterator[Session]:
    """FastAPI dependency yielding a scoped session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
