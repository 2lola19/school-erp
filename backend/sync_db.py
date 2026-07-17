import asyncio
from app.db.session import engine
from app.models.core import Base

async def instantiate_tables():
    print("[*] Synchronizing models with PostgreSQL...")
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("[+] Database synchronization complete. Tables instantiated.")

asyncio.run(instantiate_tables())