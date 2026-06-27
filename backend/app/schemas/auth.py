from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional


class SignupPayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str = Field(..., min_length=1, max_length=255)
    password: str = Field(..., min_length=6, max_length=128)


class LoginPayload(BaseModel):
    email: str
    password: str


class AuthResponse(BaseModel):
    token: str
    user_id: int
    name: str
    email: Optional[str] = None
    is_guest: bool


class MigratePayload(BaseModel):
    name: str = Field(..., min_length=1, max_length=255)
    email: str
    password: str = Field(..., min_length=6, max_length=128)


class UserInfoResponse(BaseModel):
    user_id: int
    name: str
    email: Optional[str] = None
    is_guest: bool
    created_at: datetime

class LimitInfoResponse(BaseModel):
    is_guest: bool
    requests_used: int
    requests_remaining: int
    limit: int
    limit_type: str  # "guest_total" or "daily"

    class Config:
        from_attributes = True
