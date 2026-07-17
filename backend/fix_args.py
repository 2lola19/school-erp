import os

service_path = "app/services/auth_service.py"

with open(service_path, "r", encoding="utf-8") as f:
    content = f.read()

# Map the parameter correctly to 'role' instead of 'role_id'
content = content.replace(
    "role_id=str(user.role_id)", 
    "role=str(user.role_id)"
)

with open(service_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[+] Token generation arguments aligned.")