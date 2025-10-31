# core/db.py
import logging
from contextlib import contextmanager
from typing import Generator

from core.settings import settings
from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import QueuePool

logger = logging.getLogger(__name__)

# Enhanced engine configuration with connection pooling
engine = create_engine(
    settings.DATABASE_URL,
    # Connection pool settings for production
    poolclass=QueuePool,
    pool_size=20,                    # Number of connections to maintain
    max_overflow=30,                 # Additional connections if pool is full
    pool_pre_ping=True,              # Validate connections before use
    pool_recycle=3600,               # Recycle connections every hour
    # SSL and connection settings
    connect_args={
        "sslmode": "require",
        "connect_timeout": 30,
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
    """Dependency to get database session"""
    db = SessionLocal()
    try:
        yield db
    except Exception as e:
        logger.error(f"Database session error: {e}")
        db.rollback()
        raise
    finally:
        db.close()


@contextmanager
def get_db_context():
    """Context manager for database sessions"""
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


# Event listeners for connection monitoring
@event.listens_for(engine, "connect")
def receive_connect(dbapi_connection, connection_record):
    """Log new database connections"""
    logger.debug("New database connection established")


@event.listens_for(engine, "checkout")
def receive_checkout(dbapi_connection, connection_record, connection_proxy):
    """Log connection checkout from pool"""
    logger.debug("Connection checked out from pool")


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