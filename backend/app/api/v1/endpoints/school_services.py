from datetime import datetime, timedelta, timezone
from decimal import Decimal
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.v1.dependencies import get_current_user, get_rls_db, require_permissions
from app.models.core import (
    AcademicSession,
    Activity,
    ActivityAchievement,
    ActivityAttendance,
    ActivityEnrollment,
    AuditLog,
    BreakGlassAccess,
    CounsellingCase,
    CounsellingEncounter,
    EmergencyHealthFlag,
    FeeSchedule,
    HealthEncounter,
    HealthRecord,
    Hostel,
    HostelAssignment,
    HostelRoom,
    Invoice,
    LibraryItem,
    LibraryLoan,
    MedicalConsent,
    Payment,
    RefundRequest,
    Staff,
    Student,
    TransportAssignment,
    TransportRoute,
    User,
)
from app.schemas.auth import CurrentUser
from app.schemas.school_services import (
    AchievementCreate,
    AchievementResponse,
    ActivityAttendanceCreate,
    ActivityAttendanceResponse,
    ActivityCreate,
    ActivityEnrollmentCreate,
    ActivityEnrollmentResponse,
    ActivityResponse,
    BreakGlassCreate,
    BreakGlassResponse,
    CounsellingCaseCreate,
    CounsellingCaseResponse,
    CounsellingEncounterCreate,
    CounsellingEncounterResponse,
    DecisionAction,
    EmergencyFlagCreate,
    EmergencyFlagResponse,
    FeeScheduleCreate,
    FeeScheduleResponse,
    HealthEncounterCreate,
    HealthEncounterResponse,
    HealthRecordResponse,
    HealthRecordUpsert,
    HostelAssignmentCreate,
    HostelAssignmentResponse,
    HostelCreate,
    HostelResponse,
    HostelRoomCreate,
    HostelRoomResponse,
    InvoiceCreate,
    InvoiceResponse,
    LibraryItemCreate,
    LibraryItemResponse,
    LibraryLoanCreate,
    LibraryLoanResponse,
    MedicalConsentCreate,
    MedicalConsentResponse,
    PaymentCreate,
    PaymentResponse,
    RefundCreate,
    RefundResponse,
    TransportAssignmentCreate,
    TransportAssignmentResponse,
    TransportRouteCreate,
    TransportRouteResponse,
)
from app.services.access_control import ensure_permission_scope

router = APIRouter()


def _audit(
    actor: CurrentUser,
    action: str,
    entity_name: str,
    entity_id: UUID,
    *,
    reason: str | None = None,
    scope: dict | None = None,
) -> AuditLog:
    return AuditLog(
        tenant_id=actor.tenant_id,
        user_id=actor.id,
        action=action,
        entity_name=entity_name,
        entity_id=str(entity_id),
        reason=reason,
        scope=scope or {},
    )


async def _entity(
    session: AsyncSession,
    model: type,
    entity_id: UUID,
    actor: CurrentUser,
    label: str,
    *,
    lock: bool = False,
):
    query = select(model).where(model.id == entity_id, model.tenant_id == actor.tenant_id)
    if lock:
        query = query.with_for_update()
    entity = await session.scalar(query)
    if not entity:
        raise HTTPException(status_code=404, detail=f"{label} not found")
    return entity


async def _finish(session: AsyncSession, entity):
    await session.commit()
    await session.refresh(entity)
    return entity


@router.post("/finance/fee-schedules", response_model=FeeScheduleResponse, status_code=201)
async def create_fee_schedule(
    payload: FeeScheduleCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("finance.fees.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> FeeSchedule:
    if payload.academic_session_id:
        await _entity(
            session,
            AcademicSession,
            payload.academic_session_id,
            actor,
            "Academic session",
        )
    fee = FeeSchedule(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(fee)
    await session.flush()
    session.add(_audit(actor, "FEE_SCHEDULE_CREATED", "FEE_SCHEDULE", fee.id))
    return await _finish(session, fee)


@router.get("/finance/invoices", response_model=list[InvoiceResponse])
async def list_invoices(
    actor: Annotated[CurrentUser, Depends(require_permissions("finance.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
    student_id: UUID | None = None,
) -> list[Invoice]:
    query = select(Invoice).where(Invoice.tenant_id == actor.tenant_id)
    if student_id:
        query = query.where(Invoice.student_id == student_id)
    result = await session.execute(query.order_by(Invoice.created_at.desc()))
    return list(result.scalars().all())


@router.post("/finance/invoices", response_model=InvoiceResponse, status_code=201)
async def create_invoice(
    payload: InvoiceCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("finance.invoice"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Invoice:
    await _entity(session, Student, payload.student_id, actor, "Student")
    fee = await _entity(
        session, FeeSchedule, payload.fee_schedule_id, actor, "Fee schedule"
    )
    invoice = Invoice(
        tenant_id=actor.tenant_id,
        amount=fee.amount,
        balance=fee.amount,
        issued_by=actor.id,
        **payload.model_dump(),
    )
    session.add(invoice)
    await session.flush()
    session.add(_audit(actor, "INVOICE_CREATED", "INVOICE", invoice.id))
    return await _finish(session, invoice)


@router.post("/finance/payments", response_model=PaymentResponse, status_code=201)
async def record_payment(
    payload: PaymentCreate,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("finance.receive_payment"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Payment:
    invoice = await _entity(session, Invoice, payload.invoice_id, actor, "Invoice", lock=True)
    if invoice.status != "OPEN" or payload.amount > invoice.balance:
        raise HTTPException(status_code=409, detail="Payment exceeds the open invoice balance")
    payment = Payment(
        tenant_id=actor.tenant_id,
        received_by=actor.id,
        status="PENDING",
        **payload.model_dump(),
    )
    session.add(payment)
    await session.flush()
    session.add(_audit(actor, "PAYMENT_RECORDED", "PAYMENT", payment.id))
    return await _finish(session, payment)


@router.post(
    "/finance/payments/{payment_id}/decision",
    response_model=PaymentResponse,
)
async def decide_payment(
    payment_id: UUID,
    payload: DecisionAction,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("finance.approve_payment"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Payment:
    payment = await _entity(session, Payment, payment_id, actor, "Payment", lock=True)
    if payment.status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending payments can be decided")
    if payment.received_by == actor.id:
        raise HTTPException(status_code=409, detail="A payment requires independent approval")
    if payload.decision == "APPROVE":
        invoice = await _entity(
            session, Invoice, payment.invoice_id, actor, "Invoice", lock=True
        )
        if payment.amount > invoice.balance:
            raise HTTPException(status_code=409, detail="Payment exceeds the current balance")
        invoice.balance -= payment.amount
        invoice.status = "PAID" if invoice.balance == Decimal("0") else "OPEN"
        payment.status = "APPROVED"
    else:
        payment.status = "REJECTED"
    payment.approved_by = actor.id
    payment.approved_at = datetime.now(timezone.utc)
    session.add(
        _audit(
            actor,
            f"PAYMENT_{payment.status}",
            "PAYMENT",
            payment.id,
            reason=payload.reason,
        )
    )
    return await _finish(session, payment)


@router.post("/finance/refunds", response_model=RefundResponse, status_code=201)
async def request_refund(
    payload: RefundCreate,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("finance.refund.request"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> RefundRequest:
    payment = await _entity(session, Payment, payload.payment_id, actor, "Payment")
    if payment.status != "APPROVED" or payload.amount > payment.amount:
        raise HTTPException(status_code=409, detail="Refund exceeds the approved payment")
    approved = await session.scalar(
        select(func.coalesce(func.sum(RefundRequest.amount), 0)).where(
            RefundRequest.tenant_id == actor.tenant_id,
            RefundRequest.payment_id == payment.id,
            RefundRequest.status == "APPROVED",
        )
    )
    if Decimal(approved) + payload.amount > payment.amount:
        raise HTTPException(status_code=409, detail="Approved refunds exceed the payment")
    refund = RefundRequest(
        tenant_id=actor.tenant_id,
        requested_by=actor.id,
        status="PENDING",
        **payload.model_dump(),
    )
    session.add(refund)
    await session.flush()
    session.add(
        _audit(actor, "REFUND_REQUESTED", "REFUND_REQUEST", refund.id, reason=payload.reason)
    )
    return await _finish(session, refund)


@router.post("/finance/refunds/{refund_id}/decision", response_model=RefundResponse)
async def decide_refund(
    refund_id: UUID,
    payload: DecisionAction,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("finance.refund.approve"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> RefundRequest:
    refund = await _entity(
        session, RefundRequest, refund_id, actor, "Refund request", lock=True
    )
    if refund.status != "PENDING":
        raise HTTPException(status_code=409, detail="Only pending refunds can be decided")
    if refund.requested_by == actor.id:
        raise HTTPException(status_code=409, detail="A refund requires independent approval")
    if payload.decision == "APPROVE":
        payment = await _entity(
            session, Payment, refund.payment_id, actor, "Payment", lock=True
        )
        approved = await session.scalar(
            select(func.coalesce(func.sum(RefundRequest.amount), 0)).where(
                RefundRequest.tenant_id == actor.tenant_id,
                RefundRequest.payment_id == payment.id,
                RefundRequest.status == "APPROVED",
                RefundRequest.id != refund.id,
            )
        )
        if Decimal(approved) + refund.amount > payment.amount:
            raise HTTPException(status_code=409, detail="Approved refunds exceed the payment")
        invoice = await _entity(
            session, Invoice, payment.invoice_id, actor, "Invoice", lock=True
        )
        invoice.balance += refund.amount
        invoice.status = "OPEN"
        refund.status = "APPROVED"
    else:
        refund.status = "REJECTED"
    refund.approved_by = actor.id
    refund.approved_at = datetime.now(timezone.utc)
    session.add(
        _audit(
            actor,
            f"REFUND_{refund.status}",
            "REFUND_REQUEST",
            refund.id,
            reason=payload.reason,
        )
    )
    return await _finish(session, refund)


@router.put("/health/records", response_model=HealthRecordResponse)
async def upsert_health_record(
    payload: HealthRecordUpsert,
    actor: Annotated[CurrentUser, Depends(require_permissions("health.records.write"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> HealthRecord:
    await _entity(session, Student, payload.student_id, actor, "Student")
    record = await session.scalar(
        select(HealthRecord)
        .where(
            HealthRecord.tenant_id == actor.tenant_id,
            HealthRecord.student_id == payload.student_id,
        )
        .with_for_update()
    )
    values = payload.model_dump(exclude={"student_id"})
    if record:
        for field, value in values.items():
            setattr(record, field, value)
        action = "HEALTH_RECORD_UPDATED"
    else:
        record = HealthRecord(
            tenant_id=actor.tenant_id,
            student_id=payload.student_id,
            updated_by=actor.id,
            **values,
        )
        session.add(record)
        action = "HEALTH_RECORD_CREATED"
    record.updated_by = actor.id
    await session.flush()
    session.add(
        _audit(
            actor,
            action,
            "HEALTH_RECORD",
            record.id,
            scope={"student_id": str(record.student_id)},
        )
    )
    return await _finish(session, record)


@router.get("/health/records/{student_id}", response_model=HealthRecordResponse)
async def get_health_record(
    student_id: UUID,
    actor: Annotated[CurrentUser, Depends(get_current_user)],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> HealthRecord:
    access_mode = "STANDARD"
    if "health.records.read" not in actor.permissions:
        emergency_access = await session.scalar(
            select(BreakGlassAccess.id).where(
                BreakGlassAccess.tenant_id == actor.tenant_id,
                BreakGlassAccess.user_id == actor.id,
                BreakGlassAccess.student_id == student_id,
                BreakGlassAccess.status == "ACTIVE",
                BreakGlassAccess.expires_at > datetime.now(timezone.utc),
            )
        )
        if not emergency_access:
            raise HTTPException(status_code=403, detail="Health record access is not authorized")
        access_mode = "BREAK_GLASS"
    record = await session.scalar(
        select(HealthRecord).where(
            HealthRecord.tenant_id == actor.tenant_id,
            HealthRecord.student_id == student_id,
        )
    )
    if not record:
        raise HTTPException(status_code=404, detail="Health record not found")
    session.add(
        _audit(
            actor,
            f"HEALTH_RECORD_VIEWED_{access_mode}",
            "HEALTH_RECORD",
            record.id,
            scope={"student_id": str(student_id)},
        )
    )
    await session.commit()
    return record


@router.post("/health/encounters", response_model=HealthEncounterResponse, status_code=201)
async def create_health_encounter(
    payload: HealthEncounterCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("health.records.write"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> HealthEncounter:
    await _entity(
        session, HealthRecord, payload.health_record_id, actor, "Health record"
    )
    values = payload.model_dump(exclude={"occurred_at"})
    encounter = HealthEncounter(
        tenant_id=actor.tenant_id,
        recorded_by=actor.id,
        occurred_at=payload.occurred_at or datetime.now(timezone.utc),
        **values,
    )
    session.add(encounter)
    await session.flush()
    session.add(_audit(actor, "HEALTH_ENCOUNTER_RECORDED", "HEALTH_ENCOUNTER", encounter.id))
    return await _finish(session, encounter)


@router.post("/health/consents", response_model=MedicalConsentResponse, status_code=201)
async def create_medical_consent(
    payload: MedicalConsentCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("health.consents.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> MedicalConsent:
    await _entity(session, Student, payload.student_id, actor, "Student")
    consent = MedicalConsent(
        tenant_id=actor.tenant_id,
        recorded_by=actor.id,
        **payload.model_dump(),
    )
    session.add(consent)
    await session.flush()
    session.add(_audit(actor, "MEDICAL_CONSENT_RECORDED", "MEDICAL_CONSENT", consent.id))
    return await _finish(session, consent)


@router.post("/health/emergency-flags", response_model=EmergencyFlagResponse, status_code=201)
async def create_emergency_flag(
    payload: EmergencyFlagCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("health.records.write"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> EmergencyHealthFlag:
    await _entity(session, Student, payload.student_id, actor, "Student")
    flag = EmergencyHealthFlag(
        tenant_id=actor.tenant_id,
        updated_by=actor.id,
        **payload.model_dump(),
    )
    session.add(flag)
    await session.flush()
    session.add(_audit(actor, "EMERGENCY_HEALTH_FLAG_CREATED", "EMERGENCY_HEALTH_FLAG", flag.id))
    return await _finish(session, flag)


@router.get(
    "/health/emergency-flags/{student_id}",
    response_model=list[EmergencyFlagResponse],
)
async def list_emergency_flags(
    student_id: UUID,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("health.emergency_flags.read"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[EmergencyHealthFlag]:
    result = await session.execute(
        select(EmergencyHealthFlag).where(
            EmergencyHealthFlag.tenant_id == actor.tenant_id,
            EmergencyHealthFlag.student_id == student_id,
            EmergencyHealthFlag.is_active.is_(True),
        )
    )
    flags = list(result.scalars().all())
    session.add(
        _audit(
            actor,
            "EMERGENCY_HEALTH_FLAGS_VIEWED",
            "STUDENT",
            student_id,
            scope={"student_id": str(student_id)},
        )
    )
    await session.commit()
    return flags


@router.post("/health/break-glass", response_model=BreakGlassResponse, status_code=201)
async def grant_break_glass(
    payload: BreakGlassCreate,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("health.break_glass.grant"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> BreakGlassAccess:
    now = datetime.now(timezone.utc)
    if payload.expires_at.tzinfo is None or not (
        now < payload.expires_at <= now + timedelta(hours=8)
    ):
        raise HTTPException(status_code=400, detail="Emergency access must expire within eight hours")
    await _entity(session, User, payload.user_id, actor, "User")
    await _entity(session, Student, payload.student_id, actor, "Student")
    grant = BreakGlassAccess(
        tenant_id=actor.tenant_id,
        granted_by=actor.id,
        status="ACTIVE",
        **payload.model_dump(),
    )
    session.add(grant)
    await session.flush()
    session.add(
        _audit(
            actor,
            "BREAK_GLASS_GRANTED",
            "BREAK_GLASS_ACCESS",
            grant.id,
            reason=payload.reason,
            scope={"student_id": str(payload.student_id), "user_id": str(payload.user_id)},
        )
    )
    return await _finish(session, grant)


@router.post("/health/break-glass/{grant_id}/review", response_model=BreakGlassResponse)
async def review_break_glass(
    grant_id: UUID,
    payload: DecisionAction,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("health.break_glass.review"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> BreakGlassAccess:
    grant = await _entity(
        session, BreakGlassAccess, grant_id, actor, "Break-glass grant", lock=True
    )
    if grant.status != "ACTIVE":
        raise HTTPException(status_code=409, detail="Emergency access is already closed")
    if grant.granted_by == actor.id:
        raise HTTPException(status_code=409, detail="Emergency access requires independent review")
    grant.status = "REVIEWED" if payload.decision == "APPROVE" else "REVOKED"
    grant.reviewed_by = actor.id
    grant.reviewed_at = datetime.now(timezone.utc)
    session.add(
        _audit(
            actor,
            f"BREAK_GLASS_{grant.status}",
            "BREAK_GLASS_ACCESS",
            grant.id,
            reason=payload.reason,
        )
    )
    return await _finish(session, grant)


@router.post("/counselling/cases", response_model=CounsellingCaseResponse, status_code=201)
async def create_counselling_case(
    payload: CounsellingCaseCreate,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("counselling.cases.manage"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> CounsellingCase:
    await _entity(session, Student, payload.student_id, actor, "Student")
    await _entity(session, User, payload.assigned_counsellor_id, actor, "Counsellor")
    case = CounsellingCase(
        tenant_id=actor.tenant_id,
        created_by=actor.id,
        **payload.model_dump(),
    )
    session.add(case)
    await session.flush()
    session.add(_audit(actor, "COUNSELLING_CASE_CREATED", "COUNSELLING_CASE", case.id))
    return await _finish(session, case)


@router.get("/counselling/cases", response_model=list[CounsellingCaseResponse])
async def list_counselling_cases(
    actor: Annotated[
        CurrentUser, Depends(require_permissions("counselling.cases.read"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[CounsellingCase]:
    query = select(CounsellingCase).where(CounsellingCase.tenant_id == actor.tenant_id)
    if "counselling.cases.read.all" not in actor.permissions:
        query = query.where(CounsellingCase.assigned_counsellor_id == actor.id)
    result = await session.execute(query.order_by(CounsellingCase.created_at.desc()))
    return list(result.scalars().all())


@router.post(
    "/counselling/encounters",
    response_model=CounsellingEncounterResponse,
    status_code=201,
)
async def create_counselling_encounter(
    payload: CounsellingEncounterCreate,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("counselling.encounters.write"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> CounsellingEncounter:
    case = await _entity(session, CounsellingCase, payload.case_id, actor, "Counselling case")
    if case.assigned_counsellor_id != actor.id:
        raise HTTPException(status_code=403, detail="Counselling case is assigned to another user")
    values = payload.model_dump(exclude={"occurred_at"})
    encounter = CounsellingEncounter(
        tenant_id=actor.tenant_id,
        recorded_by=actor.id,
        occurred_at=payload.occurred_at or datetime.now(timezone.utc),
        **values,
    )
    session.add(encounter)
    await session.flush()
    session.add(
        _audit(actor, "COUNSELLING_ENCOUNTER_RECORDED", "COUNSELLING_ENCOUNTER", encounter.id)
    )
    return await _finish(session, encounter)


@router.post("/library/items", response_model=LibraryItemResponse, status_code=201)
async def create_library_item(
    payload: LibraryItemCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("library.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> LibraryItem:
    item = LibraryItem(
        tenant_id=actor.tenant_id,
        available_copies=payload.total_copies,
        **payload.model_dump(),
    )
    session.add(item)
    await session.flush()
    session.add(_audit(actor, "LIBRARY_ITEM_CREATED", "LIBRARY_ITEM", item.id))
    return await _finish(session, item)


@router.get("/library/items", response_model=list[LibraryItemResponse])
async def list_library_items(
    actor: Annotated[CurrentUser, Depends(require_permissions("library.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[LibraryItem]:
    result = await session.execute(
        select(LibraryItem)
        .where(LibraryItem.tenant_id == actor.tenant_id)
        .order_by(LibraryItem.title)
    )
    return list(result.scalars().all())


@router.post("/library/loans", response_model=LibraryLoanResponse, status_code=201)
async def issue_library_loan(
    payload: LibraryLoanCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("library.loans.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> LibraryLoan:
    item = await _entity(session, LibraryItem, payload.item_id, actor, "Library item", lock=True)
    await _entity(session, Student, payload.student_id, actor, "Student")
    if item.available_copies < 1:
        raise HTTPException(status_code=409, detail="No copy is available")
    item.available_copies -= 1
    loan = LibraryLoan(
        tenant_id=actor.tenant_id,
        issued_by=actor.id,
        **payload.model_dump(),
    )
    session.add(loan)
    await session.flush()
    session.add(_audit(actor, "LIBRARY_LOAN_ISSUED", "LIBRARY_LOAN", loan.id))
    return await _finish(session, loan)


@router.post("/library/loans/{loan_id}/return", response_model=LibraryLoanResponse)
async def return_library_loan(
    loan_id: UUID,
    actor: Annotated[CurrentUser, Depends(require_permissions("library.loans.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> LibraryLoan:
    loan = await _entity(session, LibraryLoan, loan_id, actor, "Library loan", lock=True)
    if loan.status != "ISSUED":
        raise HTTPException(status_code=409, detail="Only issued items can be returned")
    item = await _entity(session, LibraryItem, loan.item_id, actor, "Library item", lock=True)
    item.available_copies += 1
    loan.status = "RETURNED"
    loan.returned_at = datetime.now(timezone.utc)
    session.add(_audit(actor, "LIBRARY_LOAN_RETURNED", "LIBRARY_LOAN", loan.id))
    return await _finish(session, loan)


@router.post("/transport/routes", response_model=TransportRouteResponse, status_code=201)
async def create_transport_route(
    payload: TransportRouteCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("transport.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> TransportRoute:
    route = TransportRoute(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(route)
    await session.flush()
    session.add(_audit(actor, "TRANSPORT_ROUTE_CREATED", "TRANSPORT_ROUTE", route.id))
    return await _finish(session, route)


@router.get("/transport/routes", response_model=list[TransportRouteResponse])
async def list_transport_routes(
    actor: Annotated[CurrentUser, Depends(require_permissions("transport.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[TransportRoute]:
    result = await session.execute(
        select(TransportRoute)
        .where(TransportRoute.tenant_id == actor.tenant_id)
        .order_by(TransportRoute.name)
    )
    return list(result.scalars().all())


@router.post(
    "/transport/assignments",
    response_model=TransportAssignmentResponse,
    status_code=201,
)
async def assign_transport(
    payload: TransportAssignmentCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("transport.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> TransportAssignment:
    route = await _entity(
        session, TransportRoute, payload.route_id, actor, "Transport route", lock=True
    )
    await _entity(session, Student, payload.student_id, actor, "Student")
    if payload.pickup_point not in route.pickup_points:
        raise HTTPException(status_code=400, detail="Pickup point is not on this route")
    assigned = await session.scalar(
        select(func.count(TransportAssignment.id)).where(
            TransportAssignment.tenant_id == actor.tenant_id,
            TransportAssignment.route_id == route.id,
            TransportAssignment.status == "ACTIVE",
        )
    )
    if int(assigned or 0) >= route.capacity:
        raise HTTPException(status_code=409, detail="Transport route is full")
    assignment = TransportAssignment(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(assignment)
    await session.flush()
    session.add(_audit(actor, "TRANSPORT_ASSIGNED", "TRANSPORT_ASSIGNMENT", assignment.id))
    return await _finish(session, assignment)


@router.post("/hostels", response_model=HostelResponse, status_code=201)
async def create_hostel(
    payload: HostelCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("hostel.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Hostel:
    hostel = Hostel(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(hostel)
    await session.flush()
    session.add(_audit(actor, "HOSTEL_CREATED", "HOSTEL", hostel.id))
    return await _finish(session, hostel)


@router.get("/hostels", response_model=list[HostelResponse])
async def list_hostels(
    actor: Annotated[CurrentUser, Depends(require_permissions("hostel.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[Hostel]:
    result = await session.execute(
        select(Hostel).where(Hostel.tenant_id == actor.tenant_id).order_by(Hostel.name)
    )
    return list(result.scalars().all())


@router.post("/hostels/rooms", response_model=HostelRoomResponse, status_code=201)
async def create_hostel_room(
    payload: HostelRoomCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("hostel.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> HostelRoom:
    hostel = await _entity(
        session, Hostel, payload.hostel_id, actor, "Hostel", lock=True
    )
    existing_capacity = await session.scalar(
        select(func.coalesce(func.sum(HostelRoom.capacity), 0)).where(
            HostelRoom.tenant_id == actor.tenant_id,
            HostelRoom.hostel_id == hostel.id,
        )
    )
    if int(existing_capacity or 0) + payload.capacity > hostel.capacity:
        raise HTTPException(status_code=409, detail="Room capacity exceeds hostel capacity")
    room = HostelRoom(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(room)
    await session.flush()
    session.add(_audit(actor, "HOSTEL_ROOM_CREATED", "HOSTEL_ROOM", room.id))
    return await _finish(session, room)


@router.post(
    "/hostels/assignments",
    response_model=HostelAssignmentResponse,
    status_code=201,
)
async def assign_hostel_room(
    payload: HostelAssignmentCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("hostel.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> HostelAssignment:
    room = await _entity(session, HostelRoom, payload.room_id, actor, "Hostel room", lock=True)
    await _entity(session, Student, payload.student_id, actor, "Student")
    occupied = await session.scalar(
        select(func.count(HostelAssignment.id)).where(
            HostelAssignment.tenant_id == actor.tenant_id,
            HostelAssignment.room_id == room.id,
            HostelAssignment.status == "ACTIVE",
        )
    )
    if int(occupied or 0) >= room.capacity:
        raise HTTPException(status_code=409, detail="Hostel room is full")
    assignment = HostelAssignment(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(assignment)
    await session.flush()
    session.add(_audit(actor, "HOSTEL_ROOM_ASSIGNED", "HOSTEL_ASSIGNMENT", assignment.id))
    return await _finish(session, assignment)


@router.post("/activities", response_model=ActivityResponse, status_code=201)
async def create_activity(
    payload: ActivityCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("activities.manage"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> Activity:
    if payload.lead_staff_id:
        await _entity(session, Staff, payload.lead_staff_id, actor, "Lead staff")
    activity = Activity(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(activity)
    await session.flush()
    session.add(_audit(actor, "ACTIVITY_CREATED", "ACTIVITY", activity.id))
    return await _finish(session, activity)


@router.get("/activities", response_model=list[ActivityResponse])
async def list_activities(
    actor: Annotated[CurrentUser, Depends(require_permissions("activities.read"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> list[Activity]:
    result = await session.execute(
        select(Activity).where(Activity.tenant_id == actor.tenant_id).order_by(Activity.name)
    )
    return list(result.scalars().all())


@router.post(
    "/activities/enrollments",
    response_model=ActivityEnrollmentResponse,
    status_code=201,
)
async def enroll_activity(
    payload: ActivityEnrollmentCreate,
    actor: Annotated[CurrentUser, Depends(require_permissions("activities.enroll"))],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> ActivityEnrollment:
    await ensure_permission_scope(
        session,
        user_id=actor.id,
        tenant_id=actor.tenant_id,
        permission_name="activities.enroll",
        required_scope={"activity_id": payload.activity_id},
    )
    await _entity(session, Activity, payload.activity_id, actor, "Activity")
    await _entity(session, Student, payload.student_id, actor, "Student")
    enrollment = ActivityEnrollment(tenant_id=actor.tenant_id, **payload.model_dump())
    session.add(enrollment)
    await session.flush()
    session.add(_audit(actor, "ACTIVITY_ENROLLED", "ACTIVITY_ENROLLMENT", enrollment.id))
    return await _finish(session, enrollment)


@router.post(
    "/activities/attendance",
    response_model=ActivityAttendanceResponse,
    status_code=201,
)
async def mark_activity_attendance(
    payload: ActivityAttendanceCreate,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("activities.attendance"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> ActivityAttendance:
    await ensure_permission_scope(
        session,
        user_id=actor.id,
        tenant_id=actor.tenant_id,
        permission_name="activities.attendance",
        required_scope={"activity_id": payload.activity_id},
    )
    enrollment = await session.scalar(
        select(ActivityEnrollment.id).where(
            ActivityEnrollment.tenant_id == actor.tenant_id,
            ActivityEnrollment.activity_id == payload.activity_id,
            ActivityEnrollment.student_id == payload.student_id,
            ActivityEnrollment.status == "ACTIVE",
        )
    )
    if not enrollment:
        raise HTTPException(status_code=409, detail="Student is not enrolled in this activity")
    attendance = ActivityAttendance(
        tenant_id=actor.tenant_id,
        recorded_by=actor.id,
        **payload.model_dump(),
    )
    session.add(attendance)
    await session.flush()
    session.add(_audit(actor, "ACTIVITY_ATTENDANCE_RECORDED", "ACTIVITY_ATTENDANCE", attendance.id))
    return await _finish(session, attendance)


@router.post(
    "/activities/achievements",
    response_model=AchievementResponse,
    status_code=201,
)
async def submit_achievement(
    payload: AchievementCreate,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("activities.achievement.submit"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> ActivityAchievement:
    await ensure_permission_scope(
        session,
        user_id=actor.id,
        tenant_id=actor.tenant_id,
        permission_name="activities.achievement.submit",
        required_scope={"activity_id": payload.activity_id},
    )
    await _entity(session, Activity, payload.activity_id, actor, "Activity")
    await _entity(session, Student, payload.student_id, actor, "Student")
    enrollment = await session.scalar(
        select(ActivityEnrollment.id).where(
            ActivityEnrollment.tenant_id == actor.tenant_id,
            ActivityEnrollment.activity_id == payload.activity_id,
            ActivityEnrollment.student_id == payload.student_id,
            ActivityEnrollment.status == "ACTIVE",
        )
    )
    if not enrollment:
        raise HTTPException(status_code=409, detail="Student is not enrolled in this activity")
    achievement = ActivityAchievement(
        tenant_id=actor.tenant_id,
        submitted_by=actor.id,
        **payload.model_dump(),
    )
    session.add(achievement)
    await session.flush()
    session.add(_audit(actor, "ACTIVITY_ACHIEVEMENT_SUBMITTED", "ACTIVITY_ACHIEVEMENT", achievement.id))
    return await _finish(session, achievement)


@router.post(
    "/activities/achievements/{achievement_id}/decision",
    response_model=AchievementResponse,
)
async def decide_achievement(
    achievement_id: UUID,
    payload: DecisionAction,
    actor: Annotated[
        CurrentUser, Depends(require_permissions("activities.achievement.approve"))
    ],
    session: Annotated[AsyncSession, Depends(get_rls_db)],
) -> ActivityAchievement:
    achievement = await _entity(
        session,
        ActivityAchievement,
        achievement_id,
        actor,
        "Activity achievement",
        lock=True,
    )
    if achievement.status != "SUBMITTED":
        raise HTTPException(status_code=409, detail="Achievement is already decided")
    if achievement.submitted_by == actor.id:
        raise HTTPException(status_code=409, detail="Achievement requires independent approval")
    achievement.status = "APPROVED" if payload.decision == "APPROVE" else "REJECTED"
    achievement.approved_by = actor.id
    achievement.approved_at = datetime.now(timezone.utc)
    session.add(
        _audit(
            actor,
            f"ACTIVITY_ACHIEVEMENT_{achievement.status}",
            "ACTIVITY_ACHIEVEMENT",
            achievement.id,
            reason=payload.reason,
        )
    )
    return await _finish(session, achievement)
