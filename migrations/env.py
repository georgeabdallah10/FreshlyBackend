# migrations/env.py
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
import os
import sys
from pathlib import Path
# Ensure project root is on sys.path so imports like `core.db` and `models.*` work
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # repo root (FreshlyBackend)
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Load .env so DATABASE_URL is available (you already have python-dotenv installed)
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

config = context.config

# Make sure Alembic logs are configured
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- IMPORTANT: override sqlalchemy.url from the environment ---
db_url = "postgresql+psycopg://postgres:10.miami.Messi@db.pvpshqpyetlizobsgbtd.supabase.co:5432/postgres?sslmode=require"
if not db_url:
    raise RuntimeError("DATABASE_URL is missing. Ensure .env exists at the repo root.")
config.set_main_option("sqlalchemy.url", db_url)
# ---------------------------------------------------------------

# Load ORM Base and all model modules so autogenerate can see tables
try:
    from models.base import Base # Base must be exported from your app
    # Import all model modules so their tables register on Base.metadata
    from models import (
        user,
        family,
        membership,
        unit,
        ingredient,
        recipe,
        recipe_ingredient,
        diet_tag,
        user_preference,
        meal_plan,
        pantry_item,
        grocery_list,
    )
    target_metadata = Base.metadata
except Exception as e:
    print(f"[alembic env] WARNING: failed to import models for autogenerate: {e}")
    target_metadata = None


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(url=url, target_metadata=target_metadata, literal_binds=True, compare_type=True, compare_server_default=True)
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata, compare_type=True, compare_server_default=True)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()