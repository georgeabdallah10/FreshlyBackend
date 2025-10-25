# Freshly Backend

Backend for meal planning, inventory, and grocery lists — **FastAPI + SQLAlchemy + (Supabase Postgres for prod)**.

## Architecture
- API: FastAPI (Python 3.11+), SQLAlchemy 2.0, Pydantic v2.
- DB: Postgres (Supabase)
- Auth: **Option A – FastAPI JWT** (API-enforced RBAC). RLS OFF initially.
- ERD domains: Identity & membership, Personalization, Recipes, Planning, Inventory, Grocery (Pricing optional).

## Run Local
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt   # or pip install fastapi uvicorn[standard] sqlalchemy pydantic pydantic-settings python-dotenv passlib[bcrypt] psycopg[binary]
cp .env.example .env
uvicorn app.main:app --reload


	•	Swagger: http://127.0.0.1:8000/docs
	•	Health: http://127.0.0.1:8000/health
