import os

endpoint_path = "app/api/v1/endpoints/auth.py"

with open(endpoint_path, "r", encoding="utf-8") as f:
    content = f.read()

# Replace the incorrect attribute with password_hash
if "user.hashed_password" in content:
    content = content.replace("user.hashed_password", "user.password_hash")
    
with open(endpoint_path, "w", encoding="utf-8") as f:
    f.write(content)

print("[+] Auth endpoint patched to use user.password_hash.")