"""Supabase client singleton — both async (FastAPI) and sync (Celery worker)."""

from supabase import AsyncClient, Client, create_async_client, create_client

from app.core.config import settings

_async_client: AsyncClient | None = None
_sync_client: Client | None = None


async def get_supabase() -> AsyncClient:
    global _async_client
    if _async_client is None:
        _async_client = await create_async_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
        )
    return _async_client


def get_sync_supabase() -> Client:
    global _sync_client
    if _sync_client is None:
        _sync_client = create_client(
            settings.SUPABASE_URL,
            settings.SUPABASE_SERVICE_KEY,
        )
    return _sync_client


async def close_supabase() -> None:
    """No-op in supabase-py 2.x — clients manage their own connection pool."""
    pass
