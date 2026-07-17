import asyncio
import uuid
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker
from sqlalchemy import select
from app.core.config import settings
from app.models.core import Student, Classroom, Enrollment

async def execute_binding():
    engine = create_async_engine(settings.SQLALCHEMY_DATABASE_URI)
    async_session = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)
    
    print("[*] Initiating Relational Binding Sequence...")
    async with async_session() as session:
        student = (await session.execute(select(Student))).scalars().first()
        classroom = (await session.execute(select(Classroom))).scalars().first()
        
        if not student or not classroom:
            print("[-] Critical Error: Missing core entities. Ensure at least 1 Student and 1 Classroom exist via the UI.")
            await engine.dispose()
            return
            
        print(f"[*] Target Student UUID: {student.id}")
        print(f"[*] Target Classroom UUID: {classroom.id}")
        
        existing = (await session.execute(
            select(Enrollment).where(
                Enrollment.student_id == student.id, 
                Enrollment.classroom_id == classroom.id
            )
        )).scalars().first()
        
        if existing:
            print("[+] State verified: Student is already bound to the classroom.")
        else:
            new_enrollment = Enrollment(
                id=uuid.uuid4(),
                tenant_id=student.tenant_id,
                student_id=student.id,
                classroom_id=classroom.id
            )
            session.add(new_enrollment)
            await session.commit()
            print(f"[+] Relational Binding Complete. Enrollment ID: {new_enrollment.id}")
            
    await engine.dispose()

asyncio.run(execute_binding())