import os

security_py = """
import bcrypt
from datetime import datetime, timedelta, timezone
from typing import Any, Union
from jose import jwt
from app.core.config import settings

ALGORITHM = "HS256"

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(
        plain_password.encode('utf-8'), 
        hashed_password.encode('utf-8')
    )

def get_password_hash(password: str) -> str:
    return bcrypt.hashpw(
        password.encode('utf-8'), 
        bcrypt.gensalt()
    ).decode('utf-8')

def create_access_token(subject: Union[str, Any], tenant_id: str, role: str, expires_delta: timedelta = None) -> str:
    expire = datetime.now(timezone.utc) + (expires_delta if expires_delta else timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode = {"exp": expire, "sub": str(subject), "tenant_id": tenant_id, "role": role}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)
"""

with open("app/core/security.py", "w", encoding="utf-8") as f:
    f.write(security_py.strip() + "\n")

print("[+] Security module rewritten to bypass passlib.")