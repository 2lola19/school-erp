from datetime import date, time
from uuid import uuid4

import pytest
from pydantic import ValidationError

from app.db.base_class import Base
from app.models.core import Attendance, TimetableEntry
from app.schemas.academic_admin import AcademicSessionCreate, TimetableEntryCreate


def test_academic_administration_tables_are_registered() -> None:
    assert {
        "academic_sessions",
        "academic_terms",
        "guardians",
        "student_guardians",
        "applicants",
        "timetable_entries",
        "exam_cycles",
        "assessment_components",
        "report_cards",
        "report_card_entries",
    } <= set(Base.metadata.tables)


def test_attendance_has_daily_uniqueness_and_workflow_constraints() -> None:
    table = Base.metadata.tables[Attendance.__tablename__]
    constraint_names = {constraint.name for constraint in table.constraints}
    assert "uq_daily_attendance" in constraint_names
    assert "ck_attendance_status" in constraint_names
    assert "ck_attendance_workflow_status" in constraint_names


def test_timetable_has_classroom_and_teacher_conflict_constraints() -> None:
    table = Base.metadata.tables[TimetableEntry.__tablename__]
    constraint_names = {constraint.name for constraint in table.constraints}
    assert "uq_class_timetable_slot" in constraint_names
    assert "uq_teacher_timetable_slot" in constraint_names


def test_academic_session_rejects_inverted_dates() -> None:
    with pytest.raises(ValidationError):
        AcademicSessionCreate(
            name="2026/2027",
            starts_on=date(2026, 9, 1),
            ends_on=date(2026, 8, 31),
        )


def test_timetable_rejects_inverted_times() -> None:
    with pytest.raises(ValidationError):
        TimetableEntryCreate(
            term_id=uuid4(),
            classroom_id=uuid4(),
            subject_id=uuid4(),
            teacher_id=uuid4(),
            weekday=1,
            period_label="P1",
            starts_at=time(9, 0),
            ends_at=time(8, 0),
        )
