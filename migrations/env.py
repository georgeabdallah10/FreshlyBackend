# migrations/env.py
from core.settings import settings
from logging.config import fileConfig
from alembic import context
from sqlalchemy import engine_from_config, pool
import os
import sys
from pathlib import Path


# Ensure project root is on sys.path so imports like `core.db` and `models.*` work
PROJECT_ROOT = Path(__file__).resolve().parents[1]  # repo root
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

# Optional: load .env for local dev (Supabase CI/CD will inject env vars)
try:
    from dotenv import load_dotenv
    load_dotenv(PROJECT_ROOT / ".env")
except Exception:
    pass

config = context.config

# Configure Alembic logging
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# --- IMPORTANT: set sqlalchemy.url from env (no hardcoding) ---
db_url = settings.DATABASE_URL
if not db_url:
    raise RuntimeError(
        "DATABASE_URL is missing. Put it in .env for local dev or set it in the environment."
    )
config.set_main_option("sqlalchemy.url", db_url)
# --------------------------------------------------------------

# Load ORM Base and all model modules so autogenerate can see tables
from core.db import Base

# EITHER: import a single models package that itself imports all model modules…
try:
    import models as models  # noqa: F401  # this should import all your model modules
except Exception as e:
    raise RuntimeError(f"[alembic env] Failed to import models: {e}") from e

# …OR (alternative) explicitly import each model module here:
# from models import (
#     user, family, membership,
#     unit, ingredient, diet_tag,
#     recipe, recipe_ingredient,
#     meal_plan, meal_slot, meal_slot_recipe,
#     pantry_item, grocery_list, user_preference,
# )

target_metadata = Base.metadata

def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        compare_type=True,
        compare_server_default=True,
    )
    with context.begin_transaction():
        context.run_migrations()

def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
            compare_server_default=True,
        )
        with context.begin_transaction():
            context.run_migrations()

if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()