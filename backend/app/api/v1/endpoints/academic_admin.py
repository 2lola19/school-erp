from datetime import date, datetime, timezone
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import and_, false, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_rls_db, require_access
from app.core.feature_registry import FeatureCode
from app.models.core import (
    AcademicSession,
    AcademicTerm,
    Applicant,
    AssessmentComponent,
    Attendance,
    AuditLog,
    Classroom,
    Enrollment,
    ExamCycle,
    Grade,
    Guardian,
    ReportCard,
    ReportCardEntry,
    Student,
    StudentGuardian,
    Subject,
    Teacher,
    TimetableEntry,
)
from app.schemas.academic_admin import (
    AcademicSessionCreate,
    AcademicSessionResponse,
    AcademicTermCreate,
    AcademicTermResponse,
    ApplicantCreate,
    ApplicantDecision,
    ApplicantResponse,
    AssessmentComponentCreate,
    AssessmentComponentResponse,
    AttendanceCorrection,
    AttendanceMark,
    AttendanceResponse,
    ExamCycleAction,
    ExamCycleCreate,
    ExamCycleResponse,
    ReportCardEntryResponse,
    ReportCardGenerate,
    ReportCardResponse,
    TimetableEntryCreate,
    TimetableEntryResponse,
    WorkflowAction,
)
from app.schemas.auth import CurrentUser
from app.services.access_control import ensure_permission_scope, get_permission_scopes

router = APIRouter()


def _audit(
    actor: CurrentUser,
    *,
    action: str,
    entity_name: str,
    entity_id: UUID,
    reason: str | None = None,
    new_values: dict | None = None,
) -> AuditLog:
    return AuditLog(
        tenant_id=actor.tenant_id,
        user_id=actor.id,
        action=action,
        entity_name=entity_name,
        entity_id=str(entity_id),
        reason=reason,
        new_values=new_values or {},
    )


async def _tenant_entity(
    session: AsyncSession, model: type, entity_id: UUID, tenant_id: UUID, label: str
):
    entity = await session.scalar(
        select(model).where(model.id == entity_id, model.tenant_id == tenant_id)
    )
    if not entity:
        raise HTTPException(status_code=400, detail=f"{label} does not belong to this tenant")
    return entity


def _scoped_filter(model: type, scopes: list[dict], fields: tuple[str, ...]):
    clauses = []
    for scope in scopes:
        predicates = []
        for field in fields:
            assigned = scope.get(field)
            if assigned is None:
                continue
            values = assigned if isinstance(assigned, list) else [assigned]
            try:
                identifiers = [UUID(str(value)) for value in values]
            except ValueError:
                continue
            predicates.append(getattr(model, field).in_(identifiers))
        if predicates:
            clauses.append(and_(*predicates))
    return or_(*clauses) if clauses else false()


@router.post("/sessions", response_model=AcademicSessionResponse, status_code=201)
async def create_session(
    payload: AcademicSessionCreate,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.CLASSES_MANAGE, "academic.setup.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> AcademicSession:
    academic_session = AcademicSession(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(academic_session)
    await session.flush()
    session.add(
        _audit(
            actor,
            action="ACADEMIC_SESSION_CREATED",
            entity_name="ACADEMIC_SESSION",
            entity_id=academic_session.id,
        )
    )
    await session.commit()
    await session.refresh(academic_session)
    return academic_session


@router.get("/sessions", response_model=list[AcademicSessionResponse])
async def list_sessions(
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.CLASSES_MANAGE, "academic.setup.read", write=False))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[AcademicSession]:
    result = await session.execute(
        select(AcademicSession)
        .where(AcademicSession.tenant_id == actor.tenant_id)
        .order_by(AcademicSession.starts_on.desc())
    )
    return list(result.scalars().all())


@router.post("/sessions/{session_id}/activate", response_model=AcademicSessionResponse)
async def activate_session(
    session_id: UUID,
    action: WorkflowAction,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.CLASSES_MANAGE, "academic.setup.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> AcademicSession:
    target = await session.scalar(
        select(AcademicSession)
        .where(
            AcademicSession.id == session_id,
            AcademicSession.tenant_id == actor.tenant_id,
        )
        .with_for_update()
    )
    if not target:
        raise HTTPException(status_code=404, detail="Academic session not found")
    active = await session.execute(
        select(AcademicSession)
        .where(
            AcademicSession.tenant_id == actor.tenant_id,
            AcademicSession.status == "ACTIVE",
            AcademicSession.id != target.id,
        )
        .with_for_update()
    )
    for current in active.scalars().all():
        current.status = "CLOSED"
    target.status = "ACTIVE"
    session.add(
        _audit(
            actor,
            action="ACADEMIC_SESSION_ACTIVATED",
            entity_name="ACADEMIC_SESSION",
            entity_id=target.id,
            reason=action.reason,
        )
    )
    await session.commit()
    await session.refresh(target)
    return target


@router.post("/terms", response_model=AcademicTermResponse, status_code=201)
async def create_term(
    payload: AcademicTermCreate,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.CLASSES_MANAGE, "academic.setup.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> AcademicTerm:
    academic_session = await _tenant_entity(
        session, AcademicSession, payload.session_id, actor.tenant_id, "Academic session"
    )
    if payload.starts_on < academic_session.starts_on or payload.ends_on > academic_session.ends_on:
        raise HTTPException(status_code=400, detail="Term dates must fall inside the session")
    term = AcademicTerm(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(term)
    await session.flush()
    session.add(
        _audit(
            actor,
            action="ACADEMIC_TERM_CREATED",
            entity_name="ACADEMIC_TERM",
            entity_id=term.id,
        )
    )
    await session.commit()
    await session.refresh(term)
    return term


@router.get("/terms", response_model=list[AcademicTermResponse])
async def list_terms(
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.CLASSES_MANAGE, "academic.setup.read", write=False))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    session_id: UUID | None = None,
) -> list[AcademicTerm]:
    query = select(AcademicTerm).where(AcademicTerm.tenant_id == actor.tenant_id)
    if session_id:
        query = query.where(AcademicTerm.session_id == session_id)
    result = await session.execute(query.order_by(AcademicTerm.starts_on.desc()))
    return list(result.scalars().all())


@router.post("/applicants", response_model=ApplicantResponse, status_code=201)
async def create_applicant(
    payload: ApplicantCreate,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.ADMISSIONS_MANAGE, "admissions.create"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Applicant:
    existing = await session.scalar(
        select(Applicant).where(
            Applicant.tenant_id == actor.tenant_id,
            Applicant.application_number == payload.application_number,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Application number already exists")
    guardian = await session.scalar(
        select(Guardian).where(
            Guardian.tenant_id == actor.tenant_id,
            Guardian.email == payload.guardian.email.lower(),
        )
    )
    if not guardian:
        guardian = Guardian(
            tenant_id=actor.tenant_id,
            first_name=payload.guardian.first_name,
            last_name=payload.guardian.last_name,
            email=payload.guardian.email.lower(),
            phone=payload.guardian.phone,
        )
        session.add(guardian)
        await session.flush()
    applicant = Applicant(
        tenant_id=actor.tenant_id,
        application_number=payload.application_number,
        first_name=payload.first_name,
        last_name=payload.last_name,
        date_of_birth=payload.date_of_birth,
        guardian_id=guardian.id,
        guardian_relationship=payload.guardian.relationship,
        status="SUBMITTED",
    )
    session.add(applicant)
    await session.flush()
    session.add(
        _audit(
            actor,
            action="APPLICATION_SUBMITTED",
            entity_name="APPLICANT",
            entity_id=applicant.id,
        )
    )
    await session.commit()
    await session.refresh(applicant)
    return applicant


@router.get("/applicants", response_model=list[ApplicantResponse])
async def list_applicants(
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.ADMISSIONS_MANAGE, "admissions.read", write=False))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    application_status: Annotated[str | None, Query(alias="status")] = None,
) -> list[Applicant]:
    query = select(Applicant).where(Applicant.tenant_id == actor.tenant_id)
    if application_status:
        query = query.where(Applicant.status == application_status.upper())
    result = await session.execute(query.order_by(Applicant.created_at.desc()))
    return list(result.scalars().all())


@router.post("/applicants/{applicant_id}/decision", response_model=ApplicantResponse)
async def decide_applicant(
    applicant_id: UUID,
    payload: ApplicantDecision,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.ADMISSIONS_MANAGE, "admissions.approve"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Applicant:
    applicant = await session.scalar(
        select(Applicant)
        .where(Applicant.id == applicant_id, Applicant.tenant_id == actor.tenant_id)
        .with_for_update()
    )
    if not applicant:
        raise HTTPException(status_code=404, detail="Applicant not found")
    if applicant.status != "SUBMITTED":
        raise HTTPException(status_code=409, detail="Only submitted applications can be decided")

    if payload.decision == "ADMIT":
        duplicate = await session.scalar(
            select(Student.id).where(
                Student.tenant_id == actor.tenant_id,
                Student.admission_number == payload.admission_number,
            )
        )
        if duplicate:
            raise HTTPException(status_code=409, detail="Admission number already exists")
        student = Student(
            tenant_id=actor.tenant_id,
            first_name=applicant.first_name,
            last_name=applicant.last_name,
            admission_number=payload.admission_number,
            date_of_birth=applicant.date_of_birth,
        )
        session.add(student)
        await session.flush()
        if applicant.guardian_id:
            session.add(
                StudentGuardian(
                    tenant_id=actor.tenant_id,
                    student_id=student.id,
                    guardian_id=applicant.guardian_id,
                    relationship=applicant.guardian_relationship,
                    is_primary=True,
                )
            )
        if payload.classroom_id:
            await _tenant_entity(
                session, Classroom, payload.classroom_id, actor.tenant_id, "Classroom"
            )
            session.add(
                Enrollment(
                    tenant_id=actor.tenant_id,
                    student_id=student.id,
                    classroom_id=payload.classroom_id,
                )
            )
        applicant.admitted_student_id = student.id
        applicant.status = "ADMITTED"
    else:
        applicant.status = "REJECTED"

    applicant.reviewed_by = actor.id
    applicant.reviewed_at = datetime.now(timezone.utc)
    applicant.decision_reason = payload.reason
    session.add(
        _audit(
            actor,
            action=f"APPLICATION_{applicant.status}",
            entity_name="APPLICANT",
            entity_id=applicant.id,
            reason=payload.reason,
        )
    )
    await session.commit()
    await session.refresh(applicant)
    return applicant


@router.post("/attendance", response_model=AttendanceResponse, status_code=201)
async def mark_attendance(
    payload: AttendanceMark,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.ATTENDANCE_MANAGE, "attendance.mark"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Attendance:
    await ensure_permission_scope(
        session,
        user_id=actor.id,
        tenant_id=actor.tenant_id,
        permission_name="attendance.mark",
        required_scope={"classroom_id": payload.classroom_id},
    )
    await _tenant_entity(session, Student, payload.student_id, actor.tenant_id, "Student")
    await _tenant_entity(
        session, Classroom, payload.classroom_id, actor.tenant_id, "Classroom"
    )
    existing = await session.scalar(
        select(Attendance.id).where(
            Attendance.tenant_id == actor.tenant_id,
            Attendance.student_id == payload.student_id,
            Attendance.classroom_id == payload.classroom_id,
            Attendance.date == payload.date,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Attendance is already recorded")
    attendance = Attendance(
        tenant_id=actor.tenant_id,
        recorded_by=actor.id,
        workflow_status="DRAFT",
        **payload.model_dump(),
    )
    session.add(attendance)
    await session.flush()
    session.add(
        _audit(
            actor,
            action="ATTENDANCE_MARKED",
            entity_name="ATTENDANCE",
            entity_id=attendance.id,
        )
    )
    await session.commit()
    await session.refresh(attendance)
    return attendance


@router.get("/attendance", response_model=list[AttendanceResponse])
async def list_attendance(
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.ATTENDANCE_MANAGE, "attendance.read", write=False))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    classroom_id: UUID | None = None,
    attendance_date: Annotated[date | None, Query(alias="date")] = None,
) -> list[Attendance]:
    query = select(Attendance).where(Attendance.tenant_id == actor.tenant_id)
    scopes = await get_permission_scopes(
        session,
        user_id=actor.id,
        tenant_id=actor.tenant_id,
        permission_name="attendance.read",
    )
    if scopes is not None:
        query = query.where(_scoped_filter(Attendance, scopes, ("classroom_id",)))
    if classroom_id:
        await ensure_permission_scope(
            session,
            user_id=actor.id,
            tenant_id=actor.tenant_id,
            permission_name="attendance.read",
            required_scope={"classroom_id": classroom_id},
        )
        query = query.where(Attendance.classroom_id == classroom_id)
    if attendance_date:
        query = query.where(Attendance.date == attendance_date)
    result = await session.execute(query.order_by(Attendance.date.desc()))
    return list(result.scalars().all())


@router.patch("/attendance/{attendance_id}", response_model=AttendanceResponse)
async def correct_attendance(
    attendance_id: UUID,
    payload: AttendanceCorrection,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.ATTENDANCE_MANAGE, "attendance.correct"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Attendance:
    attendance = await session.scalar(
        select(Attendance)
        .where(Attendance.id == attendance_id, Attendance.tenant_id == actor.tenant_id)
        .with_for_update()
    )
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    await ensure_permission_scope(
        session,
        user_id=actor.id,
        tenant_id=actor.tenant_id,
        permission_name="attendance.correct",
        required_scope={"classroom_id": attendance.classroom_id},
    )
    old_status = attendance.status
    attendance.status = payload.status
    attendance.workflow_status = "DRAFT"
    attendance.approved_by = None
    attendance.correction_reason = payload.reason
    session.add(
        _audit(
            actor,
            action="ATTENDANCE_CORRECTED",
            entity_name="ATTENDANCE",
            entity_id=attendance.id,
            reason=payload.reason,
            new_values={"from": old_status, "to": payload.status},
        )
    )
    await session.commit()
    await session.refresh(attendance)
    return attendance


@router.post("/attendance/{attendance_id}/submit", response_model=AttendanceResponse)
async def submit_attendance(
    attendance_id: UUID,
    action: WorkflowAction,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.ATTENDANCE_MANAGE, "attendance.mark"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Attendance:
    attendance = await session.scalar(
        select(Attendance)
        .where(Attendance.id == attendance_id, Attendance.tenant_id == actor.tenant_id)
        .with_for_update()
    )
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if attendance.recorded_by != actor.id:
        raise HTTPException(status_code=403, detail="Only the recorder may submit attendance")
    if attendance.workflow_status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only draft attendance can be submitted")
    attendance.workflow_status = "SUBMITTED"
    session.add(
        _audit(
            actor,
            action="ATTENDANCE_SUBMITTED",
            entity_name="ATTENDANCE",
            entity_id=attendance.id,
            reason=action.reason,
        )
    )
    await session.commit()
    await session.refresh(attendance)
    return attendance


@router.post("/attendance/{attendance_id}/approve", response_model=AttendanceResponse)
async def approve_attendance(
    attendance_id: UUID,
    action: WorkflowAction,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.ATTENDANCE_MANAGE, "attendance.approve"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Attendance:
    attendance = await session.scalar(
        select(Attendance)
        .where(Attendance.id == attendance_id, Attendance.tenant_id == actor.tenant_id)
        .with_for_update()
    )
    if not attendance:
        raise HTTPException(status_code=404, detail="Attendance record not found")
    if attendance.recorded_by == actor.id:
        raise HTTPException(status_code=409, detail="Attendance requires independent approval")
    if attendance.workflow_status != "SUBMITTED":
        raise HTTPException(status_code=409, detail="Only submitted attendance can be approved")
    attendance.workflow_status = "APPROVED"
    attendance.approved_by = actor.id
    session.add(
        _audit(
            actor,
            action="ATTENDANCE_APPROVED",
            entity_name="ATTENDANCE",
            entity_id=attendance.id,
            reason=action.reason,
        )
    )
    await session.commit()
    await session.refresh(attendance)
    return attendance


@router.post("/timetable", response_model=TimetableEntryResponse, status_code=201)
async def create_timetable_entry(
    payload: TimetableEntryCreate,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.TIMETABLE_MANAGE, "timetable.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> TimetableEntry:
    for model, entity_id, label in (
        (AcademicTerm, payload.term_id, "Term"),
        (Classroom, payload.classroom_id, "Classroom"),
        (Subject, payload.subject_id, "Subject"),
        (Teacher, payload.teacher_id, "Teacher"),
    ):
        await _tenant_entity(session, model, entity_id, actor.tenant_id, label)
    conflict = await session.scalar(
        select(TimetableEntry.id).where(
            TimetableEntry.tenant_id == actor.tenant_id,
            TimetableEntry.term_id == payload.term_id,
            TimetableEntry.weekday == payload.weekday,
            TimetableEntry.period_label == payload.period_label,
            (TimetableEntry.classroom_id == payload.classroom_id)
            | (TimetableEntry.teacher_id == payload.teacher_id),
        )
    )
    if conflict:
        raise HTTPException(status_code=409, detail="Classroom or teacher has a timetable conflict")
    entry = TimetableEntry(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(entry)
    await session.flush()
    session.add(
        _audit(
            actor,
            action="TIMETABLE_ENTRY_CREATED",
            entity_name="TIMETABLE_ENTRY",
            entity_id=entry.id,
        )
    )
    await session.commit()
    await session.refresh(entry)
    return entry


@router.get("/timetable", response_model=list[TimetableEntryResponse])
async def list_timetable(
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.TIMETABLE_MANAGE, "timetable.read", write=False))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    term_id: UUID,
    classroom_id: UUID | None = None,
) -> list[TimetableEntry]:
    query = select(TimetableEntry).where(
        TimetableEntry.tenant_id == actor.tenant_id,
        TimetableEntry.term_id == term_id,
    )
    scopes = await get_permission_scopes(
        session,
        user_id=actor.id,
        tenant_id=actor.tenant_id,
        permission_name="timetable.read",
    )
    if scopes is not None:
        query = query.where(
            _scoped_filter(TimetableEntry, scopes, ("classroom_id", "subject_id"))
        )
    if classroom_id:
        await ensure_permission_scope(
            session,
            user_id=actor.id,
            tenant_id=actor.tenant_id,
            permission_name="timetable.read",
            required_scope={"classroom_id": classroom_id},
        )
        query = query.where(TimetableEntry.classroom_id == classroom_id)
    result = await session.execute(
        query.order_by(TimetableEntry.weekday, TimetableEntry.starts_at)
    )
    return list(result.scalars().all())


@router.post("/exam-cycles", response_model=ExamCycleResponse, status_code=201)
async def create_exam_cycle(
    payload: ExamCycleCreate,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.RESULTS_MANAGE, "examinations.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> ExamCycle:
    await _tenant_entity(session, AcademicTerm, payload.term_id, actor.tenant_id, "Term")
    cycle = ExamCycle(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(cycle)
    await session.flush()
    session.add(
        _audit(
            actor,
            action="EXAM_CYCLE_CREATED",
            entity_name="EXAM_CYCLE",
            entity_id=cycle.id,
        )
    )
    await session.commit()
    await session.refresh(cycle)
    return cycle


@router.get("/exam-cycles", response_model=list[ExamCycleResponse])
async def list_exam_cycles(
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.RESULTS_MANAGE, "examinations.read", write=False))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    term_id: UUID | None = None,
) -> list[ExamCycle]:
    query = select(ExamCycle).where(ExamCycle.tenant_id == actor.tenant_id)
    if term_id:
        query = query.where(ExamCycle.term_id == term_id)
    result = await session.execute(query.order_by(ExamCycle.created_at.desc()))
    return list(result.scalars().all())


@router.post("/exam-cycles/{cycle_id}/transition", response_model=ExamCycleResponse)
async def transition_exam_cycle(
    cycle_id: UUID,
    payload: ExamCycleAction,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.RESULTS_MANAGE, "examinations.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> ExamCycle:
    cycle = await session.scalar(
        select(ExamCycle)
        .where(ExamCycle.id == cycle_id, ExamCycle.tenant_id == actor.tenant_id)
        .with_for_update()
    )
    if not cycle:
        raise HTTPException(status_code=404, detail="Examination cycle not found")
    transitions = {"DRAFT": "OPEN", "OPEN": "CLOSED", "CLOSED": "PUBLISHED"}
    requested = {"OPEN": "OPEN", "CLOSE": "CLOSED", "PUBLISH": "PUBLISHED"}[
        payload.action
    ]
    if transitions.get(cycle.status) != requested:
        raise HTTPException(status_code=409, detail="Invalid examination cycle transition")
    cycle.status = requested
    if requested == "PUBLISHED":
        cycle.published_at = datetime.now(timezone.utc)
    session.add(
        _audit(
            actor,
            action=f"EXAM_CYCLE_{requested}",
            entity_name="EXAM_CYCLE",
            entity_id=cycle.id,
            reason=payload.reason,
        )
    )
    await session.commit()
    await session.refresh(cycle)
    return cycle


@router.post(
    "/assessment-components",
    response_model=AssessmentComponentResponse,
    status_code=201,
)
async def create_assessment_component(
    payload: AssessmentComponentCreate,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.RESULTS_MANAGE, "examinations.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> AssessmentComponent:
    await _tenant_entity(
        session, ExamCycle, payload.exam_cycle_id, actor.tenant_id, "Examination cycle"
    )
    await _tenant_entity(
        session, Classroom, payload.classroom_id, actor.tenant_id, "Classroom"
    )
    await _tenant_entity(session, Subject, payload.subject_id, actor.tenant_id, "Subject")
    current_weight = await session.scalar(
        select(func.coalesce(func.sum(AssessmentComponent.weight), 0)).where(
            AssessmentComponent.tenant_id == actor.tenant_id,
            AssessmentComponent.exam_cycle_id == payload.exam_cycle_id,
            AssessmentComponent.classroom_id == payload.classroom_id,
            AssessmentComponent.subject_id == payload.subject_id,
        )
    )
    if float(current_weight or 0) + payload.weight > 100:
        raise HTTPException(status_code=409, detail="Assessment component weights exceed 100")
    component = AssessmentComponent(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(component)
    await session.flush()
    session.add(
        _audit(
            actor,
            action="ASSESSMENT_COMPONENT_CREATED",
            entity_name="ASSESSMENT_COMPONENT",
            entity_id=component.id,
        )
    )
    await session.commit()
    await session.refresh(component)
    return component


def _letter_grade(score: float) -> str:
    if score >= 70:
        return "A"
    if score >= 60:
        return "B"
    if score >= 50:
        return "C"
    if score >= 45:
        return "D"
    if score >= 40:
        return "E"
    return "F"


async def _report_response(
    session: AsyncSession, report: ReportCard
) -> ReportCardResponse:
    entries = await session.execute(
        select(ReportCardEntry)
        .where(ReportCardEntry.report_card_id == report.id)
        .order_by(ReportCardEntry.subject_id)
    )
    return ReportCardResponse(
        id=report.id,
        tenant_id=report.tenant_id,
        student_id=report.student_id,
        term_id=report.term_id,
        classroom_id=report.classroom_id,
        status=report.status,
        generated_by=report.generated_by,
        approved_by=report.approved_by,
        published_at=report.published_at,
        remarks=report.remarks,
        entries=[
            ReportCardEntryResponse.model_validate(entry)
            for entry in entries.scalars().all()
        ],
    )


@router.post("/report-cards", response_model=ReportCardResponse, status_code=201)
async def generate_report_card(
    payload: ReportCardGenerate,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.RESULTS_MANAGE, "report_cards.generate"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> ReportCardResponse:
    student = await _tenant_entity(
        session, Student, payload.student_id, actor.tenant_id, "Student"
    )
    term = await _tenant_entity(
        session, AcademicTerm, payload.term_id, actor.tenant_id, "Term"
    )
    academic_session = await _tenant_entity(
        session, AcademicSession, term.session_id, actor.tenant_id, "Academic session"
    )
    await _tenant_entity(
        session, Classroom, payload.classroom_id, actor.tenant_id, "Classroom"
    )
    enrollment = await session.scalar(
        select(Enrollment.id).where(
            Enrollment.tenant_id == actor.tenant_id,
            Enrollment.student_id == student.id,
            Enrollment.classroom_id == payload.classroom_id,
        )
    )
    if not enrollment:
        raise HTTPException(status_code=409, detail="Student is not enrolled in this classroom")
    existing = await session.scalar(
        select(ReportCard.id).where(
            ReportCard.tenant_id == actor.tenant_id,
            ReportCard.student_id == student.id,
            ReportCard.term_id == term.id,
        )
    )
    if existing:
        raise HTTPException(status_code=409, detail="Report card already exists")
    scores = await session.execute(
        select(Grade.subject_id, func.avg(Grade.score))
        .where(
            Grade.tenant_id == actor.tenant_id,
            Grade.student_id == student.id,
            Grade.classroom_id == payload.classroom_id,
            Grade.term == term.name,
            Grade.academic_year == academic_session.name,
            Grade.workflow_status == "APPROVED",
        )
        .group_by(Grade.subject_id)
    )
    score_rows = scores.all()
    if not score_rows:
        raise HTTPException(status_code=409, detail="No approved grades are available")
    report = ReportCard(
        tenant_id=actor.tenant_id,
        student_id=student.id,
        term_id=term.id,
        classroom_id=payload.classroom_id,
        status="DRAFT",
        generated_by=actor.id,
        remarks=payload.remarks,
    )
    session.add(report)
    await session.flush()
    for subject_id, average in score_rows:
        score = round(float(average), 2)
        session.add(
            ReportCardEntry(
                tenant_id=actor.tenant_id,
                report_card_id=report.id,
                subject_id=subject_id,
                score=score,
                letter_grade=_letter_grade(score),
            )
        )
    session.add(
        _audit(
            actor,
            action="REPORT_CARD_GENERATED",
            entity_name="REPORT_CARD",
            entity_id=report.id,
        )
    )
    await session.commit()
    await session.refresh(report)
    return await _report_response(session, report)

@router.get("/report-cards/{report_id}", response_model=ReportCardResponse)
async def get_report_card(
    report_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.RESULTS_MANAGE, "report_cards.read", write=False))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> ReportCardResponse:
    report = await session.scalar(
        select(ReportCard).where(
            ReportCard.id == report_id, ReportCard.tenant_id == actor.tenant_id
        )
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report card not found")
    await ensure_permission_scope(
        session,
        user_id=actor.id,
        tenant_id=actor.tenant_id,
        permission_name="report_cards.read",
        required_scope={"classroom_id": report.classroom_id},
    )
    return await _report_response(session, report)


@router.post("/report-cards/{report_id}/approve", response_model=ReportCardResponse)
async def approve_report_card(
    report_id: UUID,
    action: WorkflowAction,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.RESULTS_MANAGE, "report_cards.approve"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> ReportCardResponse:
    report = await session.scalar(
        select(ReportCard)
        .where(ReportCard.id == report_id, ReportCard.tenant_id == actor.tenant_id)
        .with_for_update()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report card not found")
    if report.generated_by == actor.id:
        raise HTTPException(status_code=409, detail="Report cards require independent approval")
    if report.status != "DRAFT":
        raise HTTPException(status_code=409, detail="Only draft report cards can be approved")
    report.status = "APPROVED"
    report.approved_by = actor.id
    session.add(
        _audit(
            actor,
            action="REPORT_CARD_APPROVED",
            entity_name="REPORT_CARD",
            entity_id=report.id,
            reason=action.reason,
        )
    )
    await session.commit()
    await session.refresh(report)
    return await _report_response(session, report)


@router.post("/report-cards/{report_id}/publish", response_model=ReportCardResponse)
async def publish_report_card(
    report_id: UUID,
    action: WorkflowAction,
    actor: Annotated[CurrentUser, Depends(require_access(FeatureCode.RESULTS_PUBLISH, "report_cards.publish"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> ReportCardResponse:
    report = await session.scalar(
        select(ReportCard)
        .where(ReportCard.id == report_id, ReportCard.tenant_id == actor.tenant_id)
        .with_for_update()
    )
    if not report:
        raise HTTPException(status_code=404, detail="Report card not found")
    if report.status != "APPROVED":
        raise HTTPException(status_code=409, detail="Only approved report cards can be published")
    report.status = "PUBLISHED"
    report.published_at = datetime.now(timezone.utc)
    session.add(
        _audit(
            actor,
            action="REPORT_CARD_PUBLISHED",
            entity_name="REPORT_CARD",
            entity_id=report.id,
            reason=action.reason,
        )
    )
    await session.commit()
    await session.refresh(report)
    return await _report_response(session, report)
