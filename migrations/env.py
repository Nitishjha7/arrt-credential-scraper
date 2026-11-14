"""
Alembic setup.

The database URL is NOT stored in alembic.ini; it comes from DATABASE_URL
in .env, the same place the app reads it from. One source of truth.

Common commands (run from the project root):
    alembic upgrade head                          # create / update tables
    alembic downgrade -1                          # undo the last migration
    alembic revision --autogenerate -m "message"  # new migration after editing models.py
"""

from logging.config import fileConfig

from alembic import context

from backend import models  # noqa: F401  (import registers all tables on Base.metadata)
from backend.db import DATABASE_URL, Base, engine

config = context.config
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """`alembic upgrade head --sql` : print the SQL instead of running it."""
    context.configure(
        url=DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Normal mode: connect to MySQL and apply migrations."""
    with engine.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
