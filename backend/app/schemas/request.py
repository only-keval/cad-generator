from pydantic import BaseModel
from datetime import datetime
from typing import Optional, List
from enum import Enum


class RequestStatusSchema(str, Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class CreateRequestPayload(BaseModel):
    prompt: str


class RequestCreatedResponse(BaseModel):
    request_id: int
    status: RequestStatusSchema
    created_at: datetime

    class Config:
        from_attributes = True


class RequestResult(BaseModel):
    code: Optional[str] = None
    error: Optional[dict] = None  # {type, message, traceback}
    result_artifact_url: Optional[str] = None  # URL to download artifact
    attempts: int = 0
    agent_state: Optional[dict] = None  # Full agent state {plan, fix_history, mode, iteration, etc.}

    class Config:
        from_attributes = True


class RequestStatusResponse(BaseModel):
    request_id: int
    session_id: int
    status: RequestStatusSchema
    prompt: str
    created_at: datetime
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    result: Optional[RequestResult] = None

    class Config:
        from_attributes = True


class SessionHistoryItem(BaseModel):
    request_id: int
    prompt: str
    status: RequestStatusSchema
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
