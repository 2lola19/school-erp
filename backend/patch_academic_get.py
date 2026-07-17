import os

target_file = "app/api/v1/endpoints/academic.py"
get_routes = """
@router.get("/teachers/", response_model=List[TeacherResponse])
async def get_teachers(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    tenant = await get_tenant_id(payload, session)
    result = await session.execute(select(Teacher).where(Teacher.tenant_id == tenant))
    return result.scalars().all()

@router.get("/classrooms/", response_model=List[ClassroomResponse])
async def get_classrooms(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    tenant = await get_tenant_id(payload, session)
    result = await session.execute(select(Classroom).where(Classroom.tenant_id == tenant))
    return result.scalars().all()
"""

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

if '@router.get("/teachers/")' not in content:
    with open(target_file, "a", encoding="utf-8") as f:
        f.write("\n" + get_routes.strip() + "\n")
    print("[+] Relational GET endpoints mathematically bound and injected.")
else:
    print("[*] GET endpoints already exist.")