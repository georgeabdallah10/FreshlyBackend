# core/db.py
import logging
from contextlib import contextmanager
from typing import Generator

from core.settings import settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import NullPool, QueuePool

logger = logging.getLogger(__name__)

# Supabase has a connection limit in session mode, so we use conservative pooling
# NullPool is recommended for serverless/Supabase to avoid "MaxClientsInSessionMode" errors
engine = create_engine(
    settings.DATABASE_URL_POOLER,
    # Use NullPool for Supabase to avoid connection limit issues
    # Each request gets a fresh connection and closes it immediately
    poolclass=NullPool,
    # Connection settings
    pool_pre_ping=True,              # Validate connections before use
    connect_args={
        "sslmode": "require",
        "connect_timeout": 10,       # Reduced timeout
        "options": "-c statement_timeout=30000"  # 30 second query timeout
    },
    # Echo SQL in development
    echo=settings.APP_ENV == "local" and settings.LOG_LEVEL == "DEBUG"
)

# Session configuration
SessionLocal = sessionmaker(
    bind=engine, 
    autoflush=False, 
    autocommit=False, 
    future=True,
    expire_on_commit=False  # Keep objects accessible after commit
)


class Base(DeclarativeBase):
    pass


def get_db() -> Generator[Session, None, None]:
    """
    Dependency to get database session.
    Ensures connection is always closed to prevent Supabase MaxClientsInSessionMode errors.
    """
    db = SessionLocal()
    try:
        yield db
        # Commit if no exception occurred
        db.commit()
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        # Always close the session to return connection to pool
        db.close()
        logger.debug("Database session closed")


@contextmanager
def get_db_context():
    """
    Context manager for database sessions in non-FastAPI contexts.
    Ensures connection is always closed to prevent connection leaks.
    """
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception as e:
        logger.error(f"Database transaction error: {e}")
        db.rollback()
        raise
    finally:
        db.close()
        logger.debug("Database context session closed")


# Event listeners for connection monitoring
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Log new database connections"""
    logger.debug("New database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout from pool"""
    logger.debug("Connection checked out from pool")


@event.listens_for(engine, "close")
def receive_close(dbapi_connection, connection_record):
    """Log connection closure"""
    logger.debug("Database connection closed")


# Health check function
def check_database_health() -> bool:
    """Check if database is accessible"""
    try:
        with engine.connect() as conn:
            conn.exec_driver_sql("SELECT 1")
        return True
    except Exception as e:
        logger.error(f"Database health check failed: {e}")
        return False


def get_pool_status() -> dict:
    """
    Get current connection pool status.
    Note: With NullPool, this will show minimal stats.
    """
    try:
        pool = engine.pool
        return {
            "pool_class": pool.__class__.__name__,
            "size": getattr(pool, "size", lambda: "N/A")(),
            "checked_in": getattr(pool, "checkedin", lambda: "N/A")(),
            "overflow": getattr(pool, "overflow", lambda: "N/A")(),
        }
    except Exception as e:
        logger.error(f"Failed to get pool status: {e}")
        return {"error": str(e)}


def dispose_engine():
    """
    Dispose of all connections in the pool.
    Useful for cleanup or resetting connections.
    """
    logger.info("Disposing database engine and closing all connections")
    engine.dispose()