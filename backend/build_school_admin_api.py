import os

patch_code = """
from pydantic import BaseModel
from app.models.core import User, Role
from app.core.security import get_password_hash

class SchoolAdminCreate(BaseModel):
    email: str
    password: str
    first_name: str
    last_name: str

@router.post("/{tenant_id}/admin")
async def create_school_admin(
    tenant_id: str,
    admin_data: SchoolAdminCreate,
    session: Annotated[AsyncSession, Depends(get_db)]
):
    # 1. Verify tenant exists
    tenant_res = await session.execute(select(Tenant).where(Tenant.id == tenant_id))
    if not tenant_res.scalars().first():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Tenant not found")

    # 2. Get or create School Admin role
    role_res = await session.execute(select(Role).where(Role.name == "School Admin"))
    role = role_res.scalars().first()
    if not role:
        role = Role(name="School Admin", description="Local administrator for a specific tenant")
        session.add(role)
        await session.commit()
        await session.refresh(role)

    # 3. Check for existing user
    user_res = await session.execute(select(User).where(User.email == admin_data.email))
    if user_res.scalars().first():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Email already registered")

    # 4. Create User
    new_admin = User(
        email=admin_data.email,
        password_hash=get_password_hash(admin_data.password),
        first_name=admin_data.first_name,
        last_name=admin_data.last_name,
        role_id=role.id,
        tenant_id=tenant_id
    )
    session.add(new_admin)
    await session.commit()
    
    return {"message": "School Admin provisioned successfully", "email": new_admin.email, "tenant_id": tenant_id}
"""

target_file = "app/api/v1/endpoints/tenants.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# Only append if not already present to prevent duplicate routes
if "class SchoolAdminCreate" not in content:
    # Ensure get_password_hash is imported if not present
    if "get_password_hash" not in content:
        content = content.replace(
            "from fastapi import APIRouter, Depends, HTTPException, status",
            "from fastapi import APIRouter, Depends, HTTPException, status\nfrom app.core.security import get_password_hash"
        )
    
    with open(target_file, "a", encoding="utf-8") as f:
        f.write("\n" + patch_code.strip() + "\n")
    print("[+] School Admin provisioning endpoint successfully injected.")
else:
    print("[*] Endpoint already exists.")