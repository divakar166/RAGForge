"""API endpoint tests — requires Supabase connection."""

import pytest

pytestmark = [
    pytest.mark.asyncio,
    pytest.mark.requires_supabase,
    pytest.mark.skip(reason="Requires Supabase — run manually with SUPABASE_MODE=true"),
]
