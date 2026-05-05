from pydantic import BaseModel
from datetime import datetime
from typing import Optional


class CreateSessionPayload(BaseModel):
    user_id: int
    title: str | None = None


class UpdateSessionPayload(BaseModel):
    title: str


class SessionResponse(BaseModel):
    session_id: int
    user_id: int
    title: str | None = None
    is_active: bool
    archived_at: Optional[datetime] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True
