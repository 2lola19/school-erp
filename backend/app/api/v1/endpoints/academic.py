from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Annotated, List
import uuid

from app.api.v1.dependencies import get_db, get_current_user_payload
from app.schemas.auth import TokenPayload
from app.schemas.academic import TeacherCreate, TeacherResponse, ClassroomCreate, ClassroomResponse
from app.models.core import Teacher, Classroom, User, AuditLog

router = APIRouter()

async def get_user_and_tenant(payload: TokenPayload, session: AsyncSession):
    try:
        user_id = uuid.UUID(payload.sub)
        query = select(User).where(User.id == user_id)
    except ValueError:
        query = select(User).where(User.email == payload.sub)
        
    user = (await session.execute(query)).scalars().first()
    if not user or not user.tenant_id:
        raise HTTPException(status_code=403, detail="Unbound users cannot manipulate local academic data.")
    return user, user.tenant_id

@router.post("/teachers/", response_model=TeacherResponse)
async def create_teacher(
    data: TeacherCreate,
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    user, tenant = await get_user_and_tenant(payload, session)
    new_teacher = Teacher(tenant_id=tenant, **data.model_dump())
    
    session.add(new_teacher)
    await session.flush()  # Generate Teacher UUID without committing
    
    # ---------------- TELEMETRY HOOK ----------------
    audit = AuditLog(tenant_id=tenant, user_id=user.id, action="CREATE", entity_name="TEACHER", entity_id=str(new_teacher.id))
    session.add(audit)
    # ------------------------------------------------
    
    await session.commit() # Dual-write transaction commit
    await session.refresh(new_teacher)
    return new_teacher

@router.post("/classrooms/", response_model=ClassroomResponse)
async def create_classroom(
    data: ClassroomCreate,
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    user, tenant = await get_user_and_tenant(payload, session)
    
    if data.teacher_id:
        teacher_query = await session.execute(
            select(Teacher).where(Teacher.id == data.teacher_id, Teacher.tenant_id == tenant)
        )
        if not teacher_query.scalars().first():
            raise HTTPException(status_code=400, detail="Foreign Key Violation")

    new_class = Classroom(tenant_id=tenant, **data.model_dump())
    session.add(new_class)
    await session.flush()
    
    # ---------------- TELEMETRY HOOK ----------------
    audit = AuditLog(tenant_id=tenant, user_id=user.id, action="CREATE", entity_name="CLASSROOM", entity_id=str(new_class.id))
    session.add(audit)
    # ------------------------------------------------

    await session.commit()
    await session.refresh(new_class)
    return new_class

@router.get("/teachers/", response_model=List[TeacherResponse])
async def get_teachers(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    user, tenant = await get_user_and_tenant(payload, session)
    result = await session.execute(select(Teacher).where(Teacher.tenant_id == tenant))
    return result.scalars().all()

@router.get("/classrooms/", response_model=List[ClassroomResponse])
async def get_classrooms(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    user, tenant = await get_user_and_tenant(payload, session)
    result = await session.execute(select(Classroom).where(Classroom.tenant_id == tenant))
    return result.scalars().all()

@router.get("/audit/", response_model=list)
async def get_audit_logs(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    user, tenant = await get_user_and_tenant(payload, session)
    result = await session.execute(
        select(AuditLog.action, AuditLog.entity_name, AuditLog.entity_id, AuditLog.timestamp)
        .where(AuditLog.tenant_id == tenant)
        .order_by(AuditLog.timestamp.desc())
    )
    return [{"action": r.action, "entity": r.entity_name, "id": r.entity_id, "time": str(r.timestamp)} for r in result.all()]
