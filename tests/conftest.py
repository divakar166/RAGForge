"""Test fixtures and configuration."""

import asyncio

import pytest

pytest_plugins = []


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


def pytest_configure(config):
    config.addinivalue_line(
        "markers",
        "requires_supabase: mark test as requiring a Supabase connection",
    )
