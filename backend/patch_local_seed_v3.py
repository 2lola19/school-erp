import os

robust_seed_code = """import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select, inspect, text
from app.core.config import settings
from app.models.core import User
from passlib.context import CryptContext

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')

async def seed_local():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("[*] Accessing local host database...")
    mapper = inspect(User)
    col_names = [c.key for c in mapper.columns]
    
    async with async_session() as session:
        # 1. Resolve relational constraints dynamically
        role_id_val = None
        if 'role_id' in col_names:
            print("[*] 'role_id' constraint detected. Resolving foreign key dependency...")
            fk = list(mapper.columns['role_id'].foreign_keys)[0]
            target_table = fk.column.table.name
            target_col = fk.column.name
            
            # Query the target table for the SUPERADMIN role
            query = text(f"SELECT {target_col} FROM {target_table} WHERE name = 'SUPERADMIN'")
            result = await session.execute(query)
            role_record = result.first()
            
            if role_record:
                role_id_val = role_record[0]
                print(f"[*] Found existing SUPERADMIN role: {role_id_val}")
            else:
                print(f"[*] SUPERADMIN role missing in '{target_table}'. Forcing injection...")
                new_role_id = uuid.uuid4()
                insert_query = text(f"INSERT INTO {target_table} ({target_col}, name) VALUES (:id, 'SUPERADMIN')")
                await session.execute(insert_query, {"id": new_role_id})
                role_id_val = new_role_id
                print(f"[*] Injected SUPERADMIN role: {role_id_val}")

        # 2. Dynamically map password column
        pwd_col = 'hashed_password'
        if 'password_hash' in col_names: pwd_col = 'password_hash'
        elif 'password' in col_names: pwd_col = 'password'
        
        # 3. Construct payload
        kwargs = {
            'email': 'admin@school.com',
            pwd_col: pwd_context.hash('admin123')
        }
        
        if 'id' in col_names:
            id_type = mapper.columns['id'].type.python_type
            if id_type != int: kwargs['id'] = uuid.uuid4()
            
        if 'role' in col_names: kwargs['role'] = 'SUPERADMIN'
        if 'role_id' in col_names: kwargs['role_id'] = role_id_val
        if 'is_superuser' in col_names: kwargs['is_superuser'] = True
        if 'is_active' in col_names: kwargs['is_active'] = True
            
        result = await session.execute(select(User).where(User.email == 'admin@school.com'))
        existing_user = result.scalars().first()
        
        if existing_user:
            print(f"[*] Superadmin exists. Forcing password update...")
            setattr(existing_user, pwd_col, pwd_context.hash('admin123'))
            if 'role_id' in col_names: setattr(existing_user, 'role_id', role_id_val)
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
print("[+] Absolute relational bypass script synthesized.")