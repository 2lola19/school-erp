import pytest_asyncio

from app.db.session import engine


@pytest_asyncio.fixture(autouse=True)
async def dispose_database_pool_after_test():
    """Keep asyncpg connections on the event loop that created them."""
    yield
    await engine.dispose()
