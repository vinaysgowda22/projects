"""Database connection and session management with WAL mode."""

from contextlib import contextmanager
from pathlib import Path
from typing import Generator

from loguru import logger
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session, sessionmaker

from backend.config import get_config
from backend.models.base import Base


def get_engine():
    """Create and configure the database engine with WAL mode enabled."""
    config = get_config()
    
    # Ensure database directory exists
    db_path = Path(config.database.path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    
    # Create engine with SQLite
    engine = create_engine(
        f"sqlite:///{config.database.path}",
        connect_args={"check_same_thread": False},  # Needed for FastAPI/Streamlit sharing
        echo=False,  # Set to True for SQL query logging in development
    )
    
    # Enable WAL mode for better concurrency
    @event.listens_for(engine, "connect")
    def set_sqlite_pragma(dbapi_conn, connection_record):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA journal_mode=WAL")
        cursor.execute("PRAGMA synchronous=NORMAL")
        cursor.close()
    
    logger.info(f"Database engine created with WAL mode: {config.database.path}")
    return engine


# Global engine and session factory
_engine = None
_session_factory = None


def get_engine_singleton() -> object:
    """Get the singleton database engine."""
    global _engine
    if _engine is None:
        _engine = get_engine()
    return _engine


def get_session_factory():
    """Get the singleton session factory."""
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine_singleton(), autoflush=False, autocommit=False)
    return _session_factory


@contextmanager
def get_session() -> Generator[Session, None, None]:
    """Context manager for database sessions with automatic cleanup."""
    session_factory = get_session_factory()
    session = session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def init_db():
    """Initialize the database schema (create all tables)."""
    engine = get_engine_singleton()
    Base.metadata.create_all(bind=engine)
    logger.info("Database schema initialized")


def reset_db():
    """Drop and recreate all tables (use with caution, mainly for testing)."""
    engine = get_engine_singleton()
    # Disconnect all connections
    engine.dispose()
    
    # Delete the database file and WAL files
    config = get_config()
    db_path = Path(config.database.path)
    db_dir = db_path.parent
    
    # Delete all SQLite-related files in the database directory
    for db_file in db_dir.glob("*.db*"):
        if db_file.exists():
            db_file.unlink()
            logger.warning(f"Deleted database file: {db_file}")
    
    # Recreate the database
    Base.metadata.create_all(bind=engine)
    logger.warning("Database schema reset (database file deleted and recreated)")
