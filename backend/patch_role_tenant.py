import os

target_file = "app/api/v1/endpoints/tenant.py"

with open(target_file, "r", encoding="utf-8") as f:
    content = f.read()

# Locate the flawed role instantiation
old_logic = 'role = Role(name="School Admin", description="Local administrator for a specific tenant")'

# Replace it with the tenant-bound instantiation
new_logic = 'role = Role(name="School Admin", description="Local administrator for a specific tenant", tenant_id=target_uuid)'

if old_logic in content:
    content = content.replace(old_logic, new_logic)
    with open(target_file, "w", encoding="utf-8") as f:
        f.write(content)
    print("[+] Repaired Role instantiation. tenant_id constraint satisfied.")
else:
    print("[-] Could not find the target logic. File may have been altered.")