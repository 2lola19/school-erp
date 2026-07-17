import os

security_path = "app/core/security.py"

with open(security_path, "a", encoding="utf-8") as f:
    f.write("\n\ndef create_refresh_token(subject, expires_delta):\n")
    f.write("    from datetime import datetime, timezone\n")
    f.write("    from jose import jwt\n")
    f.write("    from app.core.config import settings\n")
    f.write("    expire = datetime.now(timezone.utc) + expires_delta\n")
    f.write("    to_encode = {'exp': expire, 'sub': str(subject), 'type': 'refresh'}\n")
    f.write("    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)\n")

print("[+] Refresh token generator injected.")