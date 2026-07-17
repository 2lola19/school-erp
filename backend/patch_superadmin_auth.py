import os

target_file = "app/api/v1/endpoints/auth.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

old_block = """    perms = []
    if user.role_id:
        perm_query = await session.execute(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == user.role_id)
        )
        perms = perm_query.scalars().all()
        
    return await auth_service.generate_tokens(user, permissions=list(perms))"""

new_block = """    perms = []
    if user.role_id:
        perm_query = await session.execute(
            select(Permission.name)
            .join(RolePermission, RolePermission.permission_id == Permission.id)
            .where(RolePermission.role_id == user.role_id)
        )
        perms = list(perm_query.scalars().all())
        
    # Architectural Override: Unbound users are Central IT
    if user.tenant_id is None and "view_all_tenants" not in perms:
        perms.append("view_all_tenants")
        
    return await auth_service.generate_tokens(user, permissions=perms)"""

if old_block in content:
    content = content.replace(old_block, new_block)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Super Admin override injected. Unbound users now have global visibility.")
else:
    print("[-] Could not find the exact code block. The file may have changed.")