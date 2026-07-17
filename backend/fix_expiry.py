import os

auth_path = "app/services/auth_service.py"

if os.path.exists(auth_path):
    with open(auth_path, "r", encoding="utf-8") as f:
        content = f.read()

    # Replace the missing attribute with 10080 (7 days in minutes)
    content = content.replace("settings.REFRESH_TOKEN_EXPIRE_MINUTES", "10080")

    with open(auth_path, "w", encoding="utf-8") as f:
        f.write(content)
        
    print("[+] Refresh token expiration hardcoded to 7 days.")
else:
    print("[-] Could not find app/services/auth_service.py")