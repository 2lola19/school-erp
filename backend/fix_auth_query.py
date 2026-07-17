import os

endpoint_path = "app/api/v1/endpoints/auth.py"

with open(endpoint_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the simple select with a joinedload for permissions
old_query = "result = await session.execute(select(User).where(User.email == creds.email))"
new_query = """from sqlalchemy.orm import selectinload
    result = await session.execute(
        select(User)
        .options(selectinload(User.role).selectinload(Role.permissions))
        .where(User.email == creds.email)
    )"""

content = content.replace(old_query, new_query)

# Ensure the Role model is imported
if "from app.models.core import User" in content:
    content = content.replace(
        "from app.models.core import User", 
        "from app.models.core import User, Role"
    )

with open(endpoint_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[+] Auth endpoint patched to load permissions eagerly.")