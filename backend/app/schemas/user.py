from pydantic import BaseModel, EmailStr
from datetime import datetime


class CreateUserPayload(BaseModel):
    name: str
    email: EmailStr


class UserResponse(BaseModel):
    user_id: int
    name: str
    email: str
    created_at: datetime

    class Config:
        from_attributes = True
