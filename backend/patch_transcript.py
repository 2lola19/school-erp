import os

perf_file = os.path.join("app", "api", "v1", "routers", "academic_performance.py")

with open(perf_file, "r", encoding="utf-8") as f:
    content = f.read()

new_endpoint = """
class TranscriptItem(BaseModel):
    id: uuid.UUID
    subject_name: str
    subject_code: str
    score: float
    term: str
    academic_year: str

@router.get("/transcripts/{student_id}", response_model=List[TranscriptItem])
async def get_student_transcript(student_id: uuid.UUID, db: AsyncSession = Depends(get_db)):
    stmt = (
        select(Grade, Subject)
        .join(Subject, Grade.subject_id == Subject.id)
        .where(Grade.student_id == student_id)
        .order_by(Grade.academic_year.desc(), Grade.term.desc(), Subject.name.asc())
    )
    result = await db.execute(stmt)
    rows = result.all()
    
    return [
        {
            "id": grade.id,
            "subject_name": subject.name,
            "subject_code": subject.code,
            "score": grade.score,
            "term": grade.term,
            "academic_year": grade.academic_year
        }
        for grade, subject in rows
    ]
"""

if "get_student_transcript" not in content:
    with open(perf_file, "a", encoding="utf-8") as f:
        f.write(new_endpoint)
    print("[+] Transcript aggregation pipeline bound to execution context.")
else:
    print("[*] Transcript endpoint already exists.")