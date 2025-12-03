# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Freshly is a FastAPI-based meal planning and family meal sharing backend. It provides:
- JWT-based authentication with refresh tokens and token revocation (Redis-backed)
- Family/household management with role-based permissions (owner/admin/member)
- Meal planning, recipes, pantry tracking, and grocery lists
- Meal sharing system with share requests between family members
- AI-powered chat features (OpenAI integration) with receipt scanning and pantry image analysis
- User preferences for dietary restrictions, allergens, and calorie goals
- Notification system for family events and meal sharing
- Rate limiting with Redis (with in-memory fallback)
- File storage integration with Supabase for user avatars

## Development Commands

### Running the Application
```bash
# Using Python directly
python3 -m uvicorn main:app --reload --host 0.0.0.0 --port 8000

# Using Docker Compose (includes Redis)
docker-compose up --build
```

### Database Migrations (Alembic)
```bash
# Create a new migration
alembic revision --autogenerate -m "description of changes"

# Apply migrations
alembic upgrade head

# Check current migration
alembic current

# Rollback one migration
alembic downgrade -1

# View migration history
alembic history
```

**IMPORTANT**: Always use `DATABASE_URL` (direct connection) for migrations, NOT `DATABASE_URL_POOLER`. The migrations/env.py is configured to use `settings.DATABASE_URL` automatically.

### Testing
```bash
# Run test scripts (located in project root)
python3 test_meal_sharing.py
python3 test_share_request_fix.py
python3 test_members_direct.py
```

Note: This project currently uses manual test scripts rather than pytest. Tests are standalone Python scripts that import from the application.

### Linting and Formatting
No specific linting configuration detected. The project uses Python type hints extensively.

## Architecture

### Database Layer

**Connection Strategy**: The app uses SQLAlchemy with **NullPool** (no connection pooling) to avoid Supabase's "MaxClientsInSessionMode" errors. Each request gets a fresh connection from the pooler URL and closes it immediately after use.

- `DATABASE_URL`: Direct connection for migrations (session mode)
- `DATABASE_URL_POOLER`: Pooler connection for API operations (transaction mode)
- Database sessions via `get_db()` dependency injection
- Context manager `get_db_context()` for non-FastAPI contexts
- All sessions automatically commit on success, rollback on error, and close in finally block

### Authentication & Security

**JWT Token System**:
- Access tokens: 30-minute expiry (short-lived for security)
- Refresh tokens: 7-day expiry (stored in Redis with rotation)
- Token blacklisting: Revoked tokens stored in Redis with TTL
- Token validation via `get_current_user()` dependency in `core/deps.py`

**Important**: The app migrated from header-based auth (`X-User-ID`) to JWT bearer tokens. Some older docs may reference the header approach, but JWT is now the standard.

### Rate Limiting

Implemented in `core/rate_limit.py` with Redis-backed distributed limiting and in-memory fallback:
- Route-specific policies (e.g., "chat", "pantry-write", "auth-register")
- Tier-aware limits (free vs pro users)
- Burst and daily quotas for AI endpoints
- Use `rate_limiter()` dependency with `require_auth=False` for unauthenticated endpoints

### Project Structure

```
routers/           # API route handlers (FastAPI routers)
├── auth.py        # Registration, login, refresh token, logout
├── families.py    # Family CRUD, member management
├── meals.py       # Meal CRUD, family attachment
├── meal_share_requests.py  # Meal sharing between users
├── chat.py        # AI chat, receipt scanning, pantry image analysis
├── pantry_items.py
├── notifications.py
└── ...

models/            # SQLAlchemy ORM models (database tables)
├── user.py
├── family.py
├── membership.py  # FamilyMembership (user-family relationship)
├── meal.py
├── meal_share_request.py
└── ...

schemas/           # Pydantic models for request/response validation
├── auth.py        # RegisterIn, LoginIn, TokenOut
├── user.py        # UserOut
├── meal.py        # MealCreate, MealOut
└── ...

crud/              # Database operations (repository pattern)
├── auth.py        # authenticate_user, create_user
├── meals.py       # create_meal, attach_meal_to_family
├── families.py
└── ...

services/          # Business logic and external service integration
├── chat_service.py           # OpenAI chat integration
├── receipt_scanner.py        # Receipt OCR/parsing
├── pantry_image_service.py   # Image analysis for pantry items
├── oauth_signup.py           # OAuth flow handling
└── user_service.py

core/              # Application core (config, database, auth)
├── settings.py    # Pydantic Settings (env vars)
├── db.py          # Database engine, session management
├── deps.py        # FastAPI dependencies (get_current_user, require_family_role)
├── security.py    # JWT encoding/decoding, password hashing, token revocation
├── rate_limit.py  # Rate limiting logic
└── ...

migrations/        # Alembic database migrations
└── versions/

utils/             # Shared utilities
├── cache.py       # InMemoryCache for rate limiting fallback
└── tasks.py       # Background task utilities
```

### Key Architectural Patterns

**Family-Based Multi-Tenancy**: Users can belong to multiple families via `FamilyMembership`. The `require_family_role()` dependency enforces role-based access (member < admin < owner).

**Meal Sharing Flow**:
1. User creates a meal (can optionally set `family_id`)
2. OR user can attach existing meal to family via `attach_meal_to_family()`
3. To share with specific users: create `MealShareRequest` via `/meal-share-requests`
4. Recipient accepts/rejects via `/meal-share-requests/{id}/accept` or `/reject`
5. On accept, meal is copied to recipient's account

**CRUD Pattern**: Database operations separated into `crud/` modules. Routers call CRUD functions rather than directly querying the database.

**Service Layer**: Complex business logic (AI features, external APIs) in `services/`. Simple CRUD stays in `crud/`.

## Environment Configuration

Copy `.env.example` to `.env` and configure:

**Critical Settings**:
- `DATABASE_URL`: Direct Postgres connection for migrations
- `DATABASE_URL_POOLER`: Supabase pooler URL for API operations
- `JWT_SECRET`: Generate with `python -c "import secrets; print(secrets.token_urlsafe(32))"`
- `REDIS_URL`: Required for token blacklisting and rate limiting (falls back to in-memory if unavailable)
- `OPENAI_API_KEY`: Optional, enables AI chat features

**Security Notes**:
- Access tokens expire in 30 minutes (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`)
- Refresh tokens expire in 7 days (configurable via `REFRESH_TOKEN_EXPIRE_DAYS`)
- Redis is essential for token revocation in production
- Use app-specific passwords for Gmail SMTP (`MAIL_PASSWORD`)

## Common Development Patterns

### Adding a New Authenticated Endpoint
```python
from core.deps import get_current_user
from models.user import User

@router.get("/my-endpoint")
def my_endpoint(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    # current_user is automatically validated via JWT
    # db session automatically commits/rollbacks/closes
    pass
```

### Adding Family Role Authorization
```python
from core.deps import require_family_role

@router.post("/families/{family_id}/admin-action")
def admin_action(
    family_id: int,
    current_user: User = Depends(require_family_role("admin")),
    db: Session = Depends(get_db)
):
    # Only users with admin or owner role can access
    pass
```

### Adding Rate Limiting
```python
from core.rate_limit import rate_limiter

@router.post("/expensive-operation")
def expensive_op(
    current_user: User = Depends(get_current_user),
    _rate_limit = Depends(rate_limiter("operation-name"))  # requires auth
):
    pass

@router.post("/public-endpoint")
def public_op(
    _rate_limit = Depends(rate_limiter("public-op", require_auth=False))
):
    pass
```

### Creating Database Migrations
1. Modify models in `models/`
2. Run `alembic revision --autogenerate -m "description"`
3. Review generated migration in `migrations/versions/`
4. Test with `alembic upgrade head`
5. Commit both model changes and migration file

**Migration Gotcha**: Empty migration files cause "Could not determine revision id" errors. Always ensure migrations have content or delete them.

## Important Implementation Details

**NullPool for Supabase**: The app uses `poolclass=NullPool` because Supabase has connection limits in session mode. This means each request gets a fresh connection. Don't try to add connection pooling without understanding the Supabase connection limits.

**JWT Import**: Use `from jwt import PyJWKError as JWTError` for JWT exceptions (not `from jwt import JWTError`). The codebase uses PyJWT library with `PyJWKError`.

**Correlation IDs**: Every request gets a correlation ID in `main.py` middleware for request tracing. Logged as `[{correlation_id}]` prefix.

**CORS Configuration**: Middleware handles CORS with different origins for local vs production (see `main.py:87-128`). The app removed `X-User-ID` from allowed headers after migrating to JWT auth.

**Settings Access**: Use `from core.settings import settings` to access environment variables. Don't use `os.getenv()` directly.

**OpenAI Integration**: Check `settings.openai_enabled` property before calling OpenAI APIs. Features gracefully degrade if API key is not configured.

## Production Deployment Notes

The production environment runs on a Linux server with:
- Systemd service: `freshly-backend.service`
- Commands: `systemctl restart freshly-backend`, `systemctl status freshly-backend`
- Logs: `journalctl -u freshly-backend -f`
- Location: `/root/FreshlyBackend`
- Virtual environment: `.venv/`

After code changes:
```bash
cd /root/FreshlyBackend
git pull origin main
source .venv/bin/activate
alembic upgrade head  # if schema changed
systemctl restart freshly-backend
systemctl status freshly-backend
```

## Debugging Tips

- Check correlation IDs in logs to trace request flow
- Use `LOG_LEVEL=DEBUG` for SQL query logging
- Verify Redis connection: check startup logs for "[REDIS OK]" or "[REDIS WARNING]"
- Database connection issues: check `[DB OK]` or `[DB ERROR]` in startup logs
- Token issues: look for `AUTH_EVENT: TOKEN_VALIDATION_FAILED` log entries
- Rate limit issues: check for `RATE_LIMIT_EXCEEDED` logs
- Migration issues: run `alembic current` to check state, `alembic history` to view chain

## File Naming Conventions

- Models: singular (e.g., `user.py`, `meal.py`)
- Routers: plural (e.g., `users.py`, `meals.py`)
- Schemas: singular or plural based on model (e.g., `user.py` contains `UserOut`, `meal.py` contains `MealCreate/MealOut`)
- CRUD modules: plural (e.g., `users.py`, `meals.py`)
- Services: descriptive (e.g., `chat_service.py`, `receipt_scanner.py`)
