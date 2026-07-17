import os

# 1. Append a V2 Token Generator to security.py
with open("app/core/security.py", "a", encoding="utf-8") as f:
    f.write("\n\ndef create_access_token_v2(subject, tenant_id, role, permissions, expires_delta):\n")
    f.write("    from datetime import datetime, timezone\n")
    f.write("    from jose import jwt\n")
    f.write("    from app.core.config import settings\n")
    f.write("    expire = datetime.now(timezone.utc) + expires_delta\n")
    f.write("    to_encode = {'exp': expire, 'sub': str(subject), 'tenant_id': str(tenant_id), 'role': str(role), 'permissions': permissions}\n")
    f.write("    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)\n")

# 2. Rip out and replace the generate_tokens function in auth_service.py
with open("app/services/auth_service.py", "r", encoding="utf-8") as f:
    lines = f.readlines()

new_lines = []
in_target = False
for line in lines:
    if line.startswith("async def generate_tokens"):
        in_target = True
        continue
    if in_target:
        # Stop deleting when we hit the next function/class or EOF
        if line.startswith("def ") or line.startswith("async def ") or line.startswith("class "):
            in_target = False
        else:
            continue
    if not in_target:
        new_lines.append(line)

with open("app/services/auth_service.py", "w", encoding="utf-8") as f:
    f.writelines(new_lines)
    
with open("app/services/auth_service.py", "a", encoding="utf-8") as f:
    f.write("\nasync def generate_tokens(user, permissions: list):\n")
    f.write("    from datetime import timedelta\n")
    f.write("    from app.core.config import settings\n")
    f.write("    from app.core.security import create_access_token_v2, create_refresh_token\n")
    f.write("    from app.schemas.auth import TokenResponse\n")
    f.write("    # Ensure permissions map to strings safely\n")
    f.write("    if permissions and not isinstance(permissions[0], str):\n")
    f.write("        perms = [p.name for p in permissions]\n")
    f.write("    else:\n")
    f.write("        perms = permissions or []\n")
    f.write("    access_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)\n")
    f.write("    access_token = create_access_token_v2(subject=user.id, tenant_id=user.tenant_id, role=user.role_id, permissions=perms, expires_delta=access_expires)\n")
    f.write("    refresh_expires = timedelta(minutes=settings.REFRESH_TOKEN_EXPIRE_MINUTES)\n")
    f.write("    refresh_token = create_refresh_token(subject=str(user.id), expires_delta=refresh_expires)\n")
    f.write("    return TokenResponse(access_token=access_token, refresh_token=refresh_token, token_type='bearer')\n")

print("[+] Token generator forcefully replaced and routed.")