from typing import Annotated
from uuid import UUID

import redis.asyncio as redis
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_redis, get_rls_db, require_permissions
from app.models.core import AuditLog, Classroom, Grade, Student, Subject, Teacher
from app.schemas.academic import (
    ClassroomCreate,
    ClassroomResponse,
    TeacherCreate,
    TeacherResponse,
    GradeCreate,
    GradeResponse,
    SubjectCreate,
    SubjectResponse,
)
from app.schemas.auth import CurrentUser
from app.schemas.roles import StaffCreate
from app.services.roles import create_staff_with_primary_role
from app.services.access_control import ensure_permission_scope

router = APIRouter()


@router.post("/teachers", response_model=TeacherResponse, status_code=201)
async def create_teacher(
    data: TeacherCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("staff.create", "roles.assign"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    redis_client: Annotated[redis.Redis, Depends(get_redis)],
) -> Teacher:
    staff = await create_staff_with_primary_role(
        session,
        redis_client,
        actor,
        StaffCreate(
            user_id=data.user_id,
            employee_number=data.employee_id,
            first_name=data.first_name,
            last_name=data.last_name,
            employment_position="Teacher",
            primary_role_id=data.primary_role_id,
            role_scope=data.role_scope,
            role_reason=data.reason,
        ),
    )
    teacher = Teacher(
        tenant_id=actor.tenant_id,
        staff_id=staff.id,
        first_name=data.first_name,
        last_name=data.last_name,
        email=data.email.lower(),
        employee_id=data.employee_id,
    )
    session.add(teacher)
    await session.flush()
    session.add(
        AuditLog(
            tenant_id=actor.tenant_id,
            user_id=actor.id,
            staff_id=staff.id,
            action="TEACHER_CREATED",
            entity_name="TEACHER",
            entity_id=str(teacher.id),
            reason=data.reason,
        )
    )
    await session.commit()
    await session.refresh(teacher)
    return teacher


@router.get("/teachers", response_model=list[TeacherResponse])
async def get_teachers(
    actor: Annotated[CurrentUser, Depends(require_permissions("staff.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[Teacher]:
    result = await session.execute(
        select(Teacher).where(Teacher.tenant_id == actor.tenant_id)
    )
    return list(result.scalars().all())


@router.post("/classrooms", response_model=ClassroomResponse, status_code=201)
async def create_classroom(
    data: ClassroomCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("classes.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Classroom:
    if data.teacher_id:
        teacher = await session.scalar(
            select(Teacher).where(
                Teacher.id == data.teacher_id,
                Teacher.tenant_id == actor.tenant_id,
            )
        )
        if not teacher:
            raise HTTPException(status_code=400, detail="Teacher does not belong to this tenant")
    classroom = Classroom(tenant_id=actor.tenant_id, **data.model_dump())
    session.add(classroom)
    await session.flush()
    session.add(
        AuditLog(
            tenant_id=actor.tenant_id,
            user_id=actor.id,
            action="CLASSROOM_CREATED",
            entity_name="CLASSROOM",
            entity_id=str(classroom.id),
        )
    )
    await session.commit()
    await session.refresh(classroom)
    return classroom


@router.get("/classrooms", response_model=list[ClassroomResponse])
async def get_classrooms(
    actor: Annotated[CurrentUser, Depends(require_permissions("classes.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[Classroom]:
    result = await session.execute(
        select(Classroom).where(Classroom.tenant_id == actor.tenant_id)
    )
    return list(result.scalars().all())


@router.get("/audit")
async def get_audit_logs(
    actor: Annotated[CurrentUser, Depends(require_permissions("audit_logs.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[dict]:
    result = await session.execute(
        select(AuditLog)
        .where(AuditLog.tenant_id == actor.tenant_id)
        .order_by(AuditLog.timestamp.desc())
        .limit(200)
    )
    return [
        {
            "action": row.action,
            "entity": row.entity_name,
            "entity_id": row.entity_id,
            "staff_id": row.staff_id,
            "reason": row.reason,
            "timestamp": row.timestamp,
        }
        for row in result.scalars().all()
    ]


@router.post("/subjects", response_model=SubjectResponse, status_code=201)
async def create_subject(
    data: SubjectCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("subjects.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Subject:
    subject = Subject(tenant_id=actor.tenant_id, name=data.name, code=data.code.upper())
    session.add(subject)
    await session.commit()
    await session.refresh(subject)
    return subject


@router.post("/grades", response_model=GradeResponse, status_code=201)
async def enter_grade(
    data: GradeCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("scores.enter"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Grade:
    await ensure_permission_scope(
        session,
        user_id=actor.id,
        tenant_id=actor.tenant_id,
        permission_name="scores.enter",
        required_scope={"classroom_id": data.classroom_id, "subject_id": data.subject_id},
    )
    student = await session.scalar(
        select(Student).where(Student.id == data.student_id, Student.tenant_id == actor.tenant_id)
    )
    subject = await session.scalar(
        select(Subject).where(Subject.id == data.subject_id, Subject.tenant_id == actor.tenant_id)
    )
    classroom = await session.scalar(
        select(Classroom).where(Classroom.id == data.classroom_id, Classroom.tenant_id == actor.tenant_id)
    )
    if not all((student, subject, classroom)):
        raise HTTPException(status_code=400, detail="Student, subject, or classroom is outside this tenant")
    grade = Grade(
        tenant_id=actor.tenant_id,
        entered_by=actor.id,
        **data.model_dump(),
    )
    session.add(grade)
    await session.commit()
    await session.refresh(grade)
    return grade


@router.post("/grades/{grade_id}/submit", response_model=GradeResponse)
async def submit_grade(
    grade_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("scores.submit"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Grade:
    grade = await session.scalar(
        select(Grade).where(Grade.id == grade_id, Grade.tenant_id == actor.tenant_id).with_for_update()
    )
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    if grade.entered_by != actor.id:
        raise HTTPException(status_code=403, detail="Only the entering teacher may submit this grade")
    if grade.workflow_status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only draft grades can be submitted")
    grade.workflow_status = "SUBMITTED"
    await session.commit()
    await session.refresh(grade)
    return grade


@router.post("/grades/{grade_id}/approve", response_model=GradeResponse)
async def approve_grade(
    grade_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("scores.approve"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Grade:
    grade = await session.scalar(
        select(Grade).where(Grade.id == grade_id, Grade.tenant_id == actor.tenant_id).with_for_update()
    )
    if not grade:
        raise HTTPException(status_code=404, detail="Grade not found")
    if grade.entered_by == actor.id:
        raise HTTPException(status_code=409, detail="A teacher cannot approve their own grade entry")
    if grade.workflow_status != "SUBMITTED":
        raise HTTPException(status_code=409, detail="Only submitted grades can be approved")
    grade.workflow_status = "APPROVED"
    grade.approved_by = actor.id
    await session.commit()
    await session.refresh(grade)
    return grade
