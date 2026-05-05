import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session as SQLSession
from sqlalchemy.pool import NullPool
from app.models.base import Base

DATABASE_URL = os.environ.get(
    "DATABASE_URL",
    "postgresql://user:password@localhost:5432/cad_generator"
)

engine = create_engine(
    DATABASE_URL,
    poolclass=NullPool if "sqlite" in DATABASE_URL else None,
    echo=False,
)

SessionLocal = sessionmaker(bind=engine, expire_on_commit=False)


def get_db() -> SQLSession:
    """Dependency for FastAPI to provide a DB session."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db():
    """Initialize the database schema."""
    Base.metadata.create_all(bind=engine)


def create_tables():
    """Explicit table creation (alternative to alembic)."""
    init_db()
