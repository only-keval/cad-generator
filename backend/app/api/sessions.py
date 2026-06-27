from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session as SQLSession

from app.db import get_db
from app.api.deps import get_current_user
from app.models import User
from app.schemas import (
    CreateSessionPayload,
    UpdateSessionPayload,
    SessionResponse,
    SessionHistoryResponse,
    SessionHistoryItem,
)
import app.services as services

router = APIRouter(prefix="/sessions", tags=["sessions"])


@router.post("", response_model=SessionResponse)
def create_session(
    payload: CreateSessionPayload,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = services.create_session(db, user_id=current_user.id, title=payload.title)
    return SessionResponse(
        session_id=session.id,
        user_id=session.user_id,
        title=session.title,
        is_active=session.is_active,
        archived_at=session.archived_at,
        created_at=session.created_at,
        updated_at=session.updated_at,
    )


@router.get("", response_model=list[SessionResponse])
def list_user_sessions(
    cursor: int = Query(None, description="Pagination cursor (session ID)"),
    limit: int = Query(50, ge=1, le=100),
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions, _ = services.list_sessions(db, current_user.id, limit=limit, cursor=cursor)
    return [
        SessionResponse(
            session_id=s.id, user_id=s.user_id, title=s.title,
            is_active=s.is_active, archived_at=s.archived_at,
            created_at=s.created_at, updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("/archived", response_model=list[SessionResponse])
def list_user_archived_sessions(
    cursor: int = Query(None, description="Pagination cursor (session ID)"),
    limit: int = Query(50, ge=1, le=100),
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    sessions, _ = services.list_archived_sessions(db, current_user.id, limit=limit, cursor=cursor)
    return [
        SessionResponse(
            session_id=s.id, user_id=s.user_id, title=s.title,
            is_active=s.is_active, archived_at=s.archived_at,
            created_at=s.created_at, updated_at=s.updated_at,
        )
        for s in sessions
    ]


@router.get("/{session_id}", response_model=SessionResponse)
def get_session(
    session_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = services.get_owned_session(db, session_id, current_user.id)
    return SessionResponse(
        session_id=session.id, user_id=session.user_id, title=session.title,
        is_active=session.is_active, archived_at=session.archived_at,
        created_at=session.created_at, updated_at=session.updated_at,
    )


@router.get("/{session_id}/history", response_model=SessionHistoryResponse)
def get_session_history(
    session_id: int,
    cursor: int = Query(None),
    limit: int = Query(50, ge=1, le=100),
    order: str = Query("desc", pattern="^(asc|desc)$"),
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    services.get_owned_session(db, session_id, current_user.id)
    requests, next_cursor = services.get_session_requests(
        db, session_id, limit=limit, cursor=cursor, order=order,
    )
    items = [
        SessionHistoryItem(
            request_id=req.id, prompt=req.prompt, status=req.status.value,
            created_at=req.created_at, completed_at=req.completed_at,
        )
        for req in requests
    ]
    return SessionHistoryResponse(
        session_id=session_id, total_count=len(requests),
        cursor=cursor, next_cursor=next_cursor, items=items,
    )


@router.delete("/{session_id}")
def close_session(
    session_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    session = services.get_owned_session(db, session_id, current_user.id)
    services.close_session(db, session_id)
    return {"session_id": session_id, "status": "closed"}


@router.post("/{session_id}/generate-title", response_model=SessionResponse)
def generate_session_title(
    session_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    services.get_owned_session(db, session_id, current_user.id)
    session = services.generate_session_title(db, session_id)
    return SessionResponse(
        session_id=session.id, user_id=session.user_id, title=session.title,
        is_active=session.is_active, archived_at=session.archived_at,
        created_at=session.created_at, updated_at=session.updated_at,
    )


@router.patch("/{session_id}", response_model=SessionResponse)
def update_session(
    session_id: int,
    payload: UpdateSessionPayload,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    services.get_owned_session(db, session_id, current_user.id)
    session = services.update_session_title(db, session_id, payload.title)
    return SessionResponse(
        session_id=session.id, user_id=session.user_id, title=session.title,
        is_active=session.is_active, archived_at=session.archived_at,
        created_at=session.created_at, updated_at=session.updated_at,
    )


@router.post("/{session_id}/archive", response_model=SessionResponse)
def archive_session_endpoint(
    session_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    services.get_owned_session(db, session_id, current_user.id)
    session = services.archive_session(db, session_id)
    return SessionResponse(
        session_id=session.id, user_id=session.user_id, title=session.title,
        is_active=session.is_active, archived_at=session.archived_at,
        created_at=session.created_at, updated_at=session.updated_at,
    )


@router.post("/{session_id}/unarchive", response_model=SessionResponse)
def unarchive_session_endpoint(
    session_id: int,
    db: SQLSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    services.get_owned_session(db, session_id, current_user.id)
    session = services.unarchive_session(db, session_id)
    return SessionResponse(
        session_id=session.id, user_id=session.user_id, title=session.title,
        is_active=session.is_active, archived_at=session.archived_at,
        created_at=session.created_at, updated_at=session.updated_at,
    )
