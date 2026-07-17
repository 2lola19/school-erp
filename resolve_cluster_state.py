import os

# 1. Patch CORS Policy
def update_cors(file_path):
    if not os.path.exists(file_path):
        return
    with open(file_path, "r", encoding="utf-8") as f:
        content = f.read()
    
    if "3000" in content and "3001" not in content:
        patched = content.replace('"http://localhost:3000"', '"http://localhost:3000", "http://localhost:3001"')
        patched = patched.replace("'http://localhost:3000'", "'http://localhost:3000', 'http://localhost:3001'")
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(patched)
        print(f"[+] CORS Origins expanded in {file_path}")

update_cors("backend/app/main.py")
update_cors("backend/app/core/config.py")

# 2. Synthesize Container Seed Script
seed_code = """import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.models.core import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def seed():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == 'admin@school.com'))
        if result.scalars().first():
            print("[*] Superadmin already exists in container volume.")
            return
            
        user = User(
            id=uuid.uuid4(),
            email='admin@school.com',
            hashed_password=pwd_context.hash('admin123'),
            role='SUPERADMIN'
        )
        session.add(user)
        await session.commit()
        print("[+] Container Superadmin seeded. Email: admin@school.com | Password: admin123")

asyncio.run(seed())
"""
with open("seed_container.py", "w", encoding="utf-8") as f:
    f.write(seed_code)
print("[+] Seed payload synthesized.")