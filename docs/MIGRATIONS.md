# Migrations (Alembic)

## Conventions
- Naming: `YYYYMMDD_HHMM_<short_description>`
- Apply in slices:  
  A Identity  
  B Personalization  
  C Recipes  
  D Planning  
  E Inventory  
  F Grocery  
  G Pricing (optional)  

- Every migration implements `upgrade()` and `downgrade()`.

## Commands (examples)
```bash
alembic init migrations
alembic revision -m "YYYYMMDD_HHMM_identity"
alembic upgrade head
alembic downgrade -1