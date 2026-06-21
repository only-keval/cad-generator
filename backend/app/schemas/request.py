from pydantic import BaseModel, Field
from datetime import datetime
from typing import Optional, List


class CreateRequestPayload(BaseModel):
    prompt: str = Field(..., min_length=1, max_length=2000)


class RequestCreatedResponse(BaseModel):
    request_id: int
    session_id: int
    status: str
    created_at: datetime

    class Config:
        from_attributes = True


class RequestResult(BaseModel):
    code: Optional[str] = None
    error: Optional[dict] = None
    artifact_url: Optional[str] = None
    attempts: int = 0
    agent_state: Optional[dict] = None

    class Config:
        from_attributes = True


class StageInfo(BaseModel):
    name: Optional[str] = None
    attempt: int = 0
    max_attempts: int = 5
    latest_code: Optional[str] = None
    latest_error: Optional[dict] = None


class TimestampsInfo(BaseModel):
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None


class RequestStatusResponse(BaseModel):
    request_id: int
    session_id: int
    status: str
    stage: Optional[StageInfo] = None
    prompt: str
    timestamps: TimestampsInfo
    result: Optional[RequestResult] = None

    class Config:
        from_attributes = True


class SessionHistoryItem(BaseModel):
    request_id: int
    prompt: str
    status: str
    created_at: datetime
    completed_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class SessionHistoryResponse(BaseModel):
    session_id: int
    total_count: int
    cursor: Optional[int] = None
    next_cursor: Optional[int] = None
    items: List[SessionHistoryItem]
