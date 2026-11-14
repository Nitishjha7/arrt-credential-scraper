"""
Database connection.

The connection string comes from the DATABASE_URL environment variable
(put it in a `.env` file at the project root - see `.env.example`).

Example:
    DATABASE_URL=mysql+pymysql://arrt_user:secret@localhost:3306/arrt_credentials
"""

import os

from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import DeclarativeBase, sessionmaker

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")
if not DATABASE_URL:
    raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env and fill it in.")

# pool_pre_ping: quietly reconnects if MySQL dropped an idle connection
engine = create_engine(DATABASE_URL, pool_pre_ping=True)
SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


class Base(DeclarativeBase):
    """All ORM models inherit from this."""
