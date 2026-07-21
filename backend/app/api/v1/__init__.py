from fastapi import APIRouter
from app.api.v1.endpoints import academic, auth, staff_roles, students, tenant

api_router = APIRouter()
api_router.include_router(auth.router, prefix="/auth", tags=["auth"])

api_router.include_router(tenant.router, prefix="/tenants", tags=["tenants"])
api_router.include_router(students.router, prefix="/students", tags=["students"])

api_router.include_router(academic.router, prefix="/academic", tags=["Academic Operations"])
api_router.include_router(staff_roles.router, prefix="/staff", tags=["Staff roles and permissions"])
