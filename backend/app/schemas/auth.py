from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class LoginCredentials(BaseModel):
    domain: str = Field(min_length=1, max_length=255)
    email: EmailStr
    password: str = Field(min_length=8, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    expires_in: int


class TokenPayload(BaseModel):
    sub: UUID
    tenant_id: UUID
    session_id: UUID
    permission_version: int = Field(ge=1)
    type: str
    iat: int | None = None
    exp: int

    model_config = ConfigDict(extra="forbid")


class CurrentUser(BaseModel):
    id: UUID
    tenant_id: UUID
    email: EmailStr
    permission_version: int
    permissions: set[str] = Field(default_factory=set)


class Workspace(BaseModel):
    assignment_id: UUID
    role_id: UUID
    name: str
    code: str
    category: str
    assignment_type: str
    scope: dict = Field(default_factory=dict)


class UserContextResponse(BaseModel):
    user_id: UUID
    tenant_id: UUID
    email: EmailStr
    permission_version: int
    permissions: list[str]
    workspaces: list[Workspace]
