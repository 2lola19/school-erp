from pydantic import BaseModel, ConfigDict
from typing import List

class LoginCredentials(BaseModel):
    domain: str = ""
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
    role: str
    permissions: List[str] = []


import typing
from pydantic import BaseModel

class TokenPayload(BaseModel):
    sub: typing.Optional[str] = None
    exp: typing.Optional[int] = None
    tenant_id: typing.Any = None
    role: typing.Any = None
    permissions: typing.List[str] = []
