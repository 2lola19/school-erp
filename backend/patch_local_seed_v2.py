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
    
    # 1. Introspect the exact mathematical structure of the User model
    mapper = inspect(User)
    col_names = [c.key for c in mapper.columns]
    print(f"[*] Discovered User Schema: {col_names}")
    
    # 2. Dynamically map password column
    pwd_col = 'hashed_password'
    if 'password_hash' in col_names: pwd_col = 'password_hash'
    elif 'password' in col_names: pwd_col = 'password'
    
    # 3. Safely construct kwargs based ONLY on existing columns
    kwargs = {
        'email': 'admin@school.com',
        pwd_col: pwd_context.hash('admin123')
    }
    
    if 'id' in col_names:
        # Check if ID requires a UUID or auto-increments
        id_type = mapper.columns['id'].type.python_type
        if id_type != int:
            kwargs['id'] = uuid.uuid4()
            
    if 'role' in col_names:
        kwargs['role'] = 'SUPERADMIN'
    if 'is_superuser' in col_names:
        kwargs['is_superuser'] = True
    if 'is_active' in col_names:
        kwargs['is_active'] = True
        
    async with async_session() as session:
        result = await session.execute(select(User).where(User.email == 'admin@school.com'))
        existing_user = result.scalars().first()
        
        if existing_user:
            print(f"[*] Superadmin exists. Updating {pwd_col}...")
            setattr(existing_user, pwd_col, pwd_context.hash('admin123'))
            if 'is_superuser' in col_names: setattr(existing_user, 'is_superuser', True)
        else:
            user = User(**kwargs)
            session.add(user)
        
        await session.commit()
        print(f"[+] Local Superadmin mathematically guaranteed. Email: admin@school.com | Password: admin123")
    await engine.dispose()

asyncio.run(seed_local())
"""

with open("local_seed.py", "w", encoding="utf-8") as f:
    f.write(robust_seed_code)
print("[+] Absolute dynamic seed script synthesized.")