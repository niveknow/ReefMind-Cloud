from pydantic import BaseModel, EmailStr


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    display_name: str = ""
    tenant_name: str = "My Reef Tank"


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    tenant_id: str
    user_id: str


class RefreshRequest(BaseModel):
    refresh_token: str
