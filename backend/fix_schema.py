import os

auth_schema = """
from pydantic import BaseModel, ConfigDict
from typing import List

class LoginCredentials(BaseModel):
    domain: str
    email: str
    password: str
    model_config = ConfigDict(from_attributes=True)

class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"

class TokenPayload(BaseModel):
    sub: str
    tenant_id: str
    role_id: str
    permissions: List[str] = []
"""

with open("app/schemas/auth.py", "w", encoding="utf-8") as f:
    f.write(auth_schema.strip() + "\n")

print("[+] Backend schema repaired.")