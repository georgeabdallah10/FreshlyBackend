# WARP.md

This file provides guidance to WARP (warp.dev) when working with code in this repository.

## Common Commands

### Environment & dependencies
- Create venv and install deps:
  ```bash
  python -m venv .venv
  source .venv/bin/activate
  pip install -r requirements.txt
  ```
- Environment configuration is driven by `core/settings.py` (`Settings` class). At minimum you will need in `.env`:
  - `APP_ENV` (e.g. `local`, `development`, `staging`, `production`)
  - `LOG_LEVEL`
  - `DATABASE_URL` and `DATABASE_URL_POOLER`
  - `JWT_SECRET`, `JWT_ALG` (defaults to `HS256`), `ACCESS_TOKEN_EXPIRE_MINUTES`
  - Mailer config: `MAIL_USERNAME`, `MAIL_PASSWORD`, `MAIL_FROM`, etc.
  - Optional but commonly used: `OPENAI_API_KEY`, `REDIS_URL`, `CORS_ORIGINS`, `ALLOWED_HOSTS`.

### Run the API locally
- Fast path (from repo root, after venv + `.env`):
  ```bash
  uvicorn main:app --reload
  ```
- Useful endpoints once running:
  - Swagger: `http://127.0.0.1:8000/docs`
  - Health: `GET /health`
  - Readiness (DB check): `GET /ready`
  - Version/debug info (includes git hash and OpenAI config flag): `GET /debug/version`

### Alembic migrations
- Migrations live in `migrations/` and are documented in `docs/MIGRATIONS.md`.
- Typical commands (run with the same venv/env vars you use for the app):
  ```bash
  alembic upgrade head        # apply all pending migrations
  alembic downgrade -1        # rollback one step
  alembic revision -m "msg"   # create a new empty migration
  ```
- `alembic.ini` currently hardcodes a Postgres URL; prefer overriding via environment / editing before running against non‑prod databases.

### Ad-hoc test scripts
There is no centralized test runner; instead, several executable scripts validate specific flows against a real database. Run them directly with Python (ensure your `.env` points at a safe DB):

- Meal sharing system:
  ```bash
  python test_meal_sharing.py
  ```
- Meal-share 500 error regression test:
  ```bash
  python test_share_request_fix.py
  ```
- Direct family-membership debug script:
  ```bash
  python test_members_direct.py
  ```

These scripts assume pre-existing users/families in the database as described in `MEAL_SHARING_DEPLOYMENT_GUIDE.md` and related docs; treat them as smoke tests against a seeded environment.

## High-Level Architecture

### Stack overview
- **Framework:** FastAPI (`main.py`) with Pydantic v2 schemas and SQLAlchemy 2.0 ORM.
- **Database:** Postgres (Supabase in production) accessed via SQLAlchemy, with Alembic migrations in `migrations/`.
- **Auth:** JWT-based auth ("Option A" in `docs/DECISIONS.md` / `docs/SECURITY.md`) with API-enforced RBAC; Supabase Auth + RLS is a future migration path.
- **Domains:** identity & families, personalization, recipes/meals/meal-plans, inventory/pantry, grocery lists, notifications, chat/AI, meal sharing.

### Entry point & middleware
- `main.py` constructs the FastAPI `app` and wires:
  - **Lifespan**: on startup, logs environment and verifies DB connectivity via `core.db.engine`; on shutdown, disposes the engine.
  - **Security middleware** (non-local envs):
    - `SecurityHeadersMiddleware` for standard security headers.
    - `RateLimitMiddleware` with per-path limits (auth and chat are throttled more aggressively) plus a default global rate limit.
  - **Host & CORS**:
    - `TrustedHostMiddleware` configured from `settings.APP_ENV`.
    - `CORSMiddleware` using either a hard-coded local list or `settings.CORS_ORIGINS` in non-local envs.
  - **Request logging**: an `http` middleware assigns a correlation ID per request, logs timing, and exposes `X-Correlation-ID`/`X-Process-Time` headers.
  - **Error handling**: global handlers for `HTTPException`, `SQLAlchemyError`, and generic exceptions return a consistent JSON shape `{error, correlation_id, status_code}`.
- Routers are included directly in `main.py` (no versioned API prefix) and are organized by domain under `routers/`.

### Configuration & environment
- `core/settings.py` defines a `Settings` class extending `BaseSettings` (Pydantic settings):
  - Parses env vars from `.env` (case-insensitive) and does CSV splitting for `CORS_ORIGINS` / `ALLOWED_HOSTS` / `ALLOWED_FILE_TYPES`.
  - Provides convenience properties `is_production`, `is_development`, and `openai_enabled` for feature gating.
- Secrets such as DB URLs and Mailer/OpenAI keys **should** come from env; some legacy files (`alembic.ini`, `core/email_utils.py`) currently embed real URLs/keys and should be treated as refactoring targets rather than copied into new code.

### Persistence layer
- `core/db.py`:
  - Builds a SQLAlchemy `engine` against `settings.DATABASE_URL_POOLER` using `NullPool` (one connection per request, suitable for Supabase session limits) and strict SSL/timeouts.
  - Exposes `SessionLocal` and the FastAPI dependency `get_db()` which commits on success, rolls back on error, and always closes the session.
  - Defines `Base` (SQLAlchemy `DeclarativeBase`) for ORM models and helper utilities like `check_database_health()`.
- Models live in `models/*.py` and map closely to the Postgres schema (families, memberships, meals, recipes, pantry items, meal plans, chat, OAuth accounts, notifications, meal_share_requests, etc.). Relationships are generally `lazy="selectin"` to avoid N+1 on nested responses.
- Alembic migrations live in `migrations/versions/` and are described in `docs/MIGRATIONS.md` (naming by timestamped domain slices: identity, personalization, recipes, planning, inventory, grocery, pricing). Many migrations are domain-specific (e.g., family support, pantry, global meal sharing, notifications, meal_share_requests).

### API layering pattern
The codebase follows a consistent layering pattern per domain:

- **Routers** (`routers/*.py`)
  - Define the HTTP API surface with `APIRouter` (e.g., `auth`, `users`, `families`, `memberships`, `meals`, `meal_share_requests`, `notifications`, `pantry_items`, `grocery_lists`, `chat`, `storage`).
  - Handle authentication/authorization via `Depends(get_current_user)` and, where needed, family-role checks via `core.deps.require_family_role`.
  - Compose CRUD/service calls and translate them into HTTP responses (status codes, error messages, and Pydantic response models).

- **Schemas** (`schemas/*.py`)
  - Pydantic v2 models for request/response payloads, often exposing **camelCase** API fields mapped to **snake_case** DB fields.
    - Example: `MealShareRequestCreate` uses `mealId` / `recipientUserId` in requests; `MealShareRequestOut` uses serialization aliases like `mealId`, `senderUserId`, `acceptedMealId`, with nested `mealDetail`/`acceptedMealDetail` of type `MealOut`.
  - Many output schemas use `from_attributes=True` or `model_config = {"from_attributes": True, ...}` to allow direct validation from ORM objects.

- **CRUD layer** (`crud/*.py`)
  - Encapsulates DB operations for each domain: simple focused functions that take a `Session` and model arguments and return ORM instances.
  - Examples:
    - `crud/meals.py` owns meal creation/update/listing and the `attach_meal_to_family` helper.
    - `crud/meal_share_requests.py` implements creation, acceptance/decline flows (including cloning meals when accepted), listing, and duplication checks.
    - `crud/notifications.py` handles notification creation, filtering, aggregation stats, and helpers to create domain-specific notifications (e.g., meal-share accepted/declined, family-member joined).

- **Services** (`services/*.py`)
  - Encapsulate higher-level business logic and integrations:
    - `services/chat_service.py`: talks to OpenAI Chat and Image APIs, manages chat conversations/history, and powers `/chat`, `/chat/generate-image`, `/chat/scan-grocery`, and `/chat/scan-grocery-proxy`. It respects `settings.openai_enabled` and centralizes error handling and response parsing.
    - `services/pantry_image_service.py`: uses the chat/image service plus Supabase storage to auto-generate and store pantry item images, updating `PantryItem.image_url`.
    - `services/user_service.py`: example service around user profiles, caching, and statistics; uses `utils.cache.cached` for per-user caching.

- **Utilities & background work**
  - `utils/cache.py`: abstraction over an in-memory async cache and optional Redis-backed cache, with a `@cached` decorator and a `cache_cleanup_task` coroutine.
  - `utils/tasks.py`: a simple in-process background `TaskManager` with helpers for common tasks (sending email, processing file uploads, generating meal plans, caching popular recipes) and a `task_cleanup_scheduler`.

### Auth, security, and RBAC
- Detailed in `docs/SECURITY.md` and `docs/DECISIONS.md`:
  - Local user table with bcrypt-hashed passwords; JWTs issued via `core.security.create_access_token` and parsed by `core.security.decode_token` and `core.deps.get_current_user`.
  - Option A is "API-enforced RBAC": authorization logic uses membership tables (`FamilyMembership`) to grant access to per-family resources; DB RLS is currently disabled.
  - `core.security.RateLimitMiddleware` provides simple in-memory, per-IP rate limiting with per-path overrides (auth and chat endpoints more restrictive) and a default global limit.
  - `core.security.SecurityHeadersMiddleware` adds standard security headers to all responses.
  - Utility helpers like `sanitize_input` and `mask_sensitive_data` exist for defense-in-depth and safe logging.

### Domain highlights
- **Users & preferences**
  - `models/user.py` defines the primary `User` entity with profile fields, password-reset and verification codes/expiries, and relationships (memberships, meal plans, pantry, preferences, chat, OAuth accounts).
  - `routers/auth.py` implements registration, password login, Supabase OAuth login/signup, email verification, and a multi-step password reset flow (code via email → short-lived reset token → password update).
  - `routers/users.py` exposes `GET /users/me`, `PATCH /users/me`, and `DELETE /users/me` using `UserOut` / `UserUpdate` schemas and `crud.users` helpers.

- **Families & RBAC**
  - Families and memberships (with `role` enum `owner/admin/member`) back family-scoped resources (meals, pantry, notifications). `require_family_role()` in `core.deps` centralizes role checks by mapping roles to numeric ranks.

- **Meals, meal plans, and meal sharing**
  - Meals and meal plans live in `models/meal*.py` and `schemas/meal*.py`, with `crud/meals.py` managing persistence.
  - `routers/meals.py` exposes `/meals/me` CRUD scoped to the authenticated user plus `POST /meals/{meal_id}/attach-family` for associating personal meals with a family; it enforces that creators own the meal and are members of the family.
  - `routers/meal_share_requests.py` and `crud/meal_share_requests.py` implement the meal-sharing feature:
    - Sending requests (`POST /meal-share-requests`) only from owners of a meal, with duplicate-request detection and self-share prevention.
    - Responding (`POST /meal-share-requests/{id}/respond`) accepts or declines requests; acceptance clones the meal for the recipient and records `accepted_meal_id`.
    - Listing endpoints (`/pending`, `/sent`, `/received`, `/accepted-meals`) return rich, nested responses via `MealShareRequestOut`.
  - Deployment guides for this system and its migrations are in `MEAL_SHARING_DEPLOYMENT_GUIDE.md` and `PRODUCTION_COMMANDS.md` (useful when reasoning about prod incidents or DB state).

- **Notifications**
  - `models/notification.py` defines a generic notification entity with type enum (`meal_share_request`, `meal_share_accepted`, `meal_share_declined`, `family_invite`, `family_member_joined`, `system`) and relations to users, meals, families, and share requests.
  - `crud/notifications.py` provides generic CRUD plus helpers for creating domain-specific notifications for meal-sharing and family membership events.
  - `routers/notifications.py` exposes endpoints to list/filter notifications, get unread counts and stats, mark read/unread, and delete individually or in bulk.

- **Chat & AI features (text + images)**
  - Documented in detail in `docs/IMAGE_FEATURES.md`.
  - `routers/chat.py` exposes:
    - `/chat/legacy` — stateless JSON-only chat for legacy clients.
    - `/chat` + `/chat/conversations*` — stateful conversations stored via `crud.chat`.
    - `/chat/generate-image` — DALL·E-based image generation using `services.chat_service.generate_image`.
    - `/chat/scan-grocery` and `/chat/scan-grocery-proxy` — Vision-based grocery/receipt scanning; the proxy endpoint accepts multipart form uploads and converts them to base64 behind the scenes.
  - `services/chat_service.py` centralizes all OpenAI integration, including:
    - Model selection (`gpt-4o-mini` for chat, `gpt-4o` for vision, `dall-e-3` for images).
    - Response caching for stateless calls.
    - Strict JSON parsing for grocery scanning, with validation and graceful degradation when parsing fails.

- **Pantry images**
  - `services/pantry_image_service.py` integrates the image-generation pipeline with Supabase storage to automatically create and persist product images for pantry items, with sanitized file paths per user/item.

## Repo-specific Notes for Future Warp Agents
- Treat `docs/` as canonical for business rules and deployment procedures (not just comments):
  - `docs/README.md` → project overview and architecture.
  - `docs/DECISIONS.md` → key DB/auth decisions (IDs, naming, enums, index strategy, auth path from local JWT to Supabase Auth + RLS).
  - `docs/SECURITY.md` → auth/authorization model, token details, and migration notes.
  - `docs/IMAGE_FEATURES.md` → API contracts for image generation and grocery scanning.
  - `docs/MIGRATIONS.md` → naming conventions and domain slicing for Alembic migrations.
- Several standalone `*.md` files in the repo root (e.g., `MEAL_SHARING_DEPLOYMENT_GUIDE.md`, `PRODUCTION_COMMANDS.md`, various `*_FIX_COMPLETE.md`) capture production-debug context and end-to-end flows; they are useful when diagnosing regressions or replicating incident fixes.
- The test scripts and many guides assume a Supabase-hosted Postgres instance with pre-seeded data; when running locally or in CI, use a separate database and adjust `.env`/`alembic.ini` accordingly to avoid touching production data.
