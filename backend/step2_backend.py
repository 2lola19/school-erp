import os

target_file = "app/api/v1/endpoints/tenant.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# Locate the vulnerable fetch block
vulnerable_block = """@router.get("/", response_model=List[TenantResponse])
async def get_tenants(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    result = await session.execute(select(Tenant))
    return result.scalars().all()"""

# Replace it with the secured block
secured_block = """@router.get("/", response_model=List[TenantResponse])
async def get_tenants(
    payload: Annotated[TokenPayload, Depends(get_current_user_payload)],
    session: Annotated[AsyncSession, Depends(get_db)]
):
    if "view_all_tenants" not in payload.permissions:
        raise HTTPException(status_code=403, detail="Global visibility restricted.")
    result = await session.execute(select(Tenant))
    return result.scalars().all()"""

if vulnerable_block in content:
    content = content.replace(vulnerable_block, secured_block)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Step 2 Complete: Backend security matrix locked.")
else:
    print("[-] Could not find the exact code block. The file may already be secured.")