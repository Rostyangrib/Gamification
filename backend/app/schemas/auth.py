from pydantic import BaseModel, EmailStr, Field


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str = Field(min_length=6)
    name: str = Field(min_length=1)


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class CheckAccessRequest(BaseModel):
    email: EmailStr


class UserResponse(BaseModel):
    id: int
    email: str
    name: str
    role: str
    department: str
    clearance_level: int
    location: str
    is_active: bool
    moodle_id: int | None = None

    model_config = {"from_attributes": True}


class AuthCheckResponse(BaseModel):
    allowed: bool
    reason: str


class ErrorResponse(BaseModel):
    detail: str
    reason: str | None = None
