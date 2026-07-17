from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from app.api.v1.dependencies import get_db
from app.models.core import Teacher, Student, Classroom, Enrollment

router = APIRouter()

@router.get("/stats")
async def get_dashboard_stats(db: AsyncSession = Depends(get_db)):
    teachers = (await db.execute(select(func.count(Teacher.id)))).scalar() or 0
    students = (await db.execute(select(func.count(Student.id)))).scalar() or 0
    classrooms = (await db.execute(select(func.count(Classroom.id)))).scalar() or 0
    enrollments = (await db.execute(select(func.count(Enrollment.id)))).scalar() or 0
    
    return {
        "teachers": teachers,
        "students": students,
        "classrooms": classrooms,
        "enrollments": enrollments
    }
