# Freshly – Decision Log (Phase 0)

## Auth Model
- Choice: **Option A – FastAPI JWT** (API-enforced RBAC). Supabase RLS OFF for now.
- Rationale: Ship faster, fewer moving parts, simpler local dev. Can migrate to Supabase Auth + RLS later.

## IDs & Keys
- Primary keys: `INTEGER` autoincrement for all tables (v1).
- Keep path to Supabase: add `users.supabase_uid UUID UNIQUE NULL` later when migrating to Supabase Auth.
- Foreign keys (selected):
  - family_memberships.family_id → CASCADE
  - family_memberships.user_id → CASCADE
  - recipes.family_id → SET NULL
  - recipe_ingredients.recipe_id → CASCADE
  - plan_entries.meal_plan_id → CASCADE
  - plan_entries.recipe_id → SET NULL
  - inventory_items.location_id → SET NULL
  - grocery_items.list_id → CASCADE

## Naming Conventions
- snake_case everywhere; plural table names (users, families, meal_plans, ...).

## Enums via CHECK (no DB enum types in v1)
- role ∈ {owner, admin, member}
- scope ∈ {user, family, global}
- meal_slot ∈ {breakfast, lunch, dinner, snack, dessert}
- location_type ∈ {fridge, freezer, pantry}
- list_status ∈ {draft, active, ordered, done}

## Indexes to add early
- Unique: users.email, families.invite_code, family_memberships(family_id,user_id), products.upc
- Perf: plan_entries(meal_plan_id,plan_date,meal_slot), inventory_items(family_id,expires_at), grocery_items(list_id,checked), recipes(family_id,scope)

## Minimal A → B Migration Note
1) Enable Supabase Auth; link each user by email; populate `users.supabase_uid`.
2) Switch API to verify Supabase JWTs; keep endpoints.
3) Turn RLS ON; write policies mirroring existing API membership checks.
4) Optionally retire local passwords after transition.