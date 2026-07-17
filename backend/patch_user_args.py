import os

target_file = "app/api/v1/endpoints/tenant.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# The exact block causing the TypeError
old_user_block = """    new_admin = User(
        email=admin_data.email,
        password_hash=get_password_hash(admin_data.password),
        first_name=admin_data.first_name,
        last_name=admin_data.last_name,
        role_id=role.id,
        tenant_id=target_uuid
    )"""

# The corrected block matching your database schema
new_user_block = """    new_admin = User(
        email=admin_data.email,
        password_hash=get_password_hash(admin_data.password),
        role_id=role.id,
        tenant_id=target_uuid
    )"""

if old_user_block in content:
    content = content.replace(old_user_block, new_user_block)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Repaired User instantiation. Removed invalid name arguments.")
else:
    print("[-] Could not find the exact User block. Verify formatting.")