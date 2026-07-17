import os

robust_seed_code = """import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, inspect
from app.core.config import settings
from app.models.core import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def seed_local():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("[*] Accessing local host database...")
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == 'admin@school.com'))
        existing_user = result.scalars().first()
        
        # Introspect the ORM to dynamically resolve the password column name
        mapper = inspect(User)
        col_names = [c.key for c in mapper.columns]
        pwd_col = 'hashed_password'
        if 'password_hash' in col_names: pwd_col = 'password_hash'
        elif 'password' in col_names: pwd_col = 'password'
        
        if existing_user:
            print(f"[*] Superadmin already exists locally. Updating {pwd_col}...")
            setattr(existing_user, pwd_col, pwd_context.hash('admin123'))
        else:
            kwargs = {
                'id': uuid.uuid4(),
                'email': 'admin@school.com',
                'role': 'SUPERADMIN',
                pwd_col: pwd_context.hash('admin123')
            }
            user = User(**kwargs)
            session.add(user)
        
        await session.commit()
        print(f"[+] Local Superadmin mathematically guaranteed using column '{pwd_col}'. Email: admin@school.com | Password: admin123")
    await engine.dispose()

asyncio.run(seed_local())
"""

with open("local_seed.py", "w", encoding="utf-8") as f:
    f.write(robust_seed_code)
print("[+] Resilient local seed script synthesized.")