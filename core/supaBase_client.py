# core/supabase_client.py
from core.settings import settings
from supabase import create_client, Client

def get_supabase_admin() -> Client:
    if not settings.SUPABASE_URL or not settings.SUPABASE_SERVICE_ROLE:
        raise RuntimeError("Supabase settings missing. Check SUPABASE_URL and SUPABASE_SERVICE_ROLE in .env")
    return create_client(settings.SUPABASE_URL, settings.SUPABASE_SERVICE_ROLE)