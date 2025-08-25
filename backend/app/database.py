from __future__ import annotations

import os
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker


def _build_sqlite_url() -> str:
    db_path = os.getenv("DATABASE_PATH", "./app.db")
    # Ensure path is relative to backend working directory
    if db_path.startswith("sqlite:"):
        return db_path
    return f"sqlite:///{db_path}"


SQLALCHEMY_DATABASE_URL = _build_sqlite_url()

# For SQLite, check_same_thread must be False for use with FastAPI
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False} if SQLALCHEMY_DATABASE_URL.startswith("sqlite") else {}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


