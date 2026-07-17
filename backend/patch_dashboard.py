import os

dashboard_file = os.path.join("app", "api", "v1", "routers", "dashboard.py")
main_file = os.path.join("app", "main.py")

dashboard_code = """from fastapi import APIRouter, Depends
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
"""

with open(dashboard_file, "w", encoding="utf-8") as f:
    f.write(dashboard_code)

with open(main_file, "r", encoding="utf-8") as f:
    main_code = f.read()

if "import dashboard" not in main_code:
    main_code = main_code.replace(
        "from app.api.v1.routers import enrollment",
        "from app.api.v1.routers import enrollment\nfrom app.api.v1.routers import dashboard"
    )
    
if "dashboard.router" not in main_code:
    main_code = main_code.replace(
        "app.include_router(enrollment.router, prefix=\"/api/v1/academic/enrollments\", tags=[\"academic\"])",
        "app.include_router(enrollment.router, prefix=\"/api/v1/academic/enrollments\", tags=[\"academic\"])\napp.include_router(dashboard.router, prefix=\"/api/v1/dashboard\", tags=[\"dashboard\"])"
    )

with open(main_file, "w", encoding="utf-8") as f:
    f.write(main_code)

print("[+] Dashboard telemetry router synthesized and bound to main application.")