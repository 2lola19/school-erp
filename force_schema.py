import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from app.core.config import settings
from app.models.core import Base

async def project_schema():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    print("[*] Initiating absolute ORM topological projection...")
    try:
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        print("[+] Complete schema graph instantiated. Relational integrity absolute.")
    except Exception as e:
        print(f"[-] Projection failed: {e}")
    finally:
        await engine.dispose()

asyncio.run(project_schema())