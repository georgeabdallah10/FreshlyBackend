# SECURITY

## Authentication (Option A – FastAPI JWT)
- Local user table with `email` (unique) + `hashed_password` (bcrypt).
- Endpoints:
  - `POST /auth/register` → create user, store bcrypt hash.
  - `POST /auth/login` → verify hash, return JWT (HS256).
  - `GET /auth/me` → validate JWT, return current user.
- Tokens:
  - Access token expiry: 24h (configurable via `ACCESS_TOKEN_EXPIRE_MINUTES`).
  - Algorithm: HS256 (env: `JWT_ALG`), secret: `JWT_SECRET`.

## Authorization (API-enforced RBAC)
- For any resource with `family_id`: API checks membership in `family_memberships`.
- Roles:
  - `owner` – full control on family resources.
  - `admin` – manage members/locations; typical write access.
  - `member` – standard usage; can be limited for certain endpoints by router.
- DB RLS: **disabled** in Option A; DB uses a single server connection.
- Later migration: can enable Supabase Auth + RLS (see DECISIONS.md).

## Password Hygiene
- Bcrypt hashing, 12+ rounds (Passlib default adequate).
- Never log passwords or password-reset tokens.
- Rate limiting/lockout: at reverse proxy or app layer (defer to deployment phase if needed).

## Secrets & Env
- `.env.example` documents required variables; `.env` not committed.
- Prod secrets stored in hosting provider’s secret manager.

## Minimal A → B Migration (Supabase Auth + RLS)
1) Map `users` to Supabase users via email; write `supabase_uid` for each.
2) Switch JWT verification to Supabase JWKs; keep the same route structure.
3) Turn RLS ON; implement policies aligned to membership/role.
4) Optionally retire local passwords or keep both during transition.