import asyncio
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
