"""
Create the MySQL database named in DATABASE_URL, if it doesn't exist yet.

Alembic creates *tables*, but it can't create the database itself, so run
this once before the first migration:

    .venv\\Scripts\\python -m backend.create_db
    .venv\\Scripts\\alembic upgrade head
"""

from sqlalchemy import create_engine, text
from sqlalchemy.engine import URL, make_url

from .db import DATABASE_URL


def main() -> None:
    url = make_url(DATABASE_URL)
    db_name = url.database

    # Connect to the server itself, without selecting a database
    # (the database doesn't exist yet, so selecting it would fail)
    server_url = URL.create(
        drivername=url.drivername,
        username=url.username,
        password=url.password,
        host=url.host,
        port=url.port,
    )
    server_engine = create_engine(server_url)
    with server_engine.connect() as conn:
        conn.execute(text(
            f"CREATE DATABASE IF NOT EXISTS `{db_name}` "
            "CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
        ))
        version = conn.execute(text("SELECT VERSION()")).scalar()

    print(f"MySQL {version} on {url.host}:{url.port} - database '{db_name}' is ready.")


if __name__ == "__main__":
    main()
