from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session as SQLSession

from app.models import User, Session as DBSession, Request as DBRequest
from app.utils import now


def create_user(db: SQLSession, name: str, email: str) -> User:
    """Create a new user."""
    user = User(name=name, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user(db: SQLSession, user_id: int) -> Optional[User]:
    """Fetch a user by ID."""
    return db.query(User).filter(User.id == user_id).first()


def create_session(db: SQLSession, user_id: int, title: Optional[str] = None) -> DBSession:
    """Create a new session for a user (initially active)."""
    session = DBSession(user_id=user_id, title=title)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session(db: SQLSession, session_id: int) -> Optional[DBSession]:
    """Fetch a session by ID."""
    return db.query(DBSession).filter(DBSession.id == session_id).first()


def close_session(db: SQLSession, session_id: int) -> Optional[DBSession]:
    """Archive a session (soft delete via archived_at timestamp)."""
    session = get_session(db, session_id)
    if session:
        session.archived_at = now()
        session.updated_at = now()
        db.commit()
        db.refresh(session)
    return session


def archive_session(db: SQLSession, session_id: int) -> Optional[DBSession]:
    """Archive a session (alias for close_session)."""
    return close_session(db, session_id)


def unarchive_session(db: SQLSession, session_id: int) -> Optional[DBSession]:
    """Unarchive a session."""
    session = get_session(db, session_id)
    if session:
        session.archived_at = None
        session.updated_at = now()
        db.commit()
        db.refresh(session)
    return session


def update_session_title(db: SQLSession, session_id: int, new_title: str) -> Optional[DBSession]:
    """Manually update a session's title."""
    session = get_session(db, session_id)
    if session:
        session.title = new_title
        session.updated_at = now()
        db.commit()
        db.refresh(session)
    return session


def generate_session_title(db: SQLSession, session_id: int) -> Optional[DBSession]:
    """Generate AI title based on session's first request (blocking).
    
    This is a blocking operation that calls the LLM.
    """
    from app.agent.llm import llm
    
    session = get_session(db, session_id)
    if not session:
        return None
    
    # Fetch first request to get context
    first_request = (
        db.query(DBRequest)
        .filter(DBRequest.session_id == session_id)
        .order_by(DBRequest.created_at.asc())
        .first()
    )
    
    if not first_request:
        # No requests yet, can't generate title
        return session
    
    # Generate title from first request prompt
    prompt = f"""Given this CAD design request, generate a short, descriptive title (2-4 words max):
    
    Request: {first_request.prompt}
    
    Title:"""
    
    try:
        title = llm(prompt).strip()
        # Clean up the title if LLM added quotes or extra text
        title = title.strip('"\'').strip()
        
        # Ensure it's reasonable length
        if len(title) > 100:
            title = title[:97] + "..."
        
        return update_session_title(db, session_id, title)
    except Exception as e:
        print(f"Failed to generate session title: {e}")
        # Return unchanged session on error
        return session


def list_sessions(
    db: SQLSession, user_id: int, limit: int = 50, cursor: Optional[int] = None
) -> tuple[list[DBSession], Optional[int]]:
    """Fetch paginated active sessions for a user, ordered by creation time (newest first)."""
    query = db.query(DBSession).filter(
        DBSession.user_id == user_id,
        DBSession.archived_at.is_(None),
    ).order_by(DBSession.created_at.desc())
    
    if cursor:
        query = query.filter(DBSession.id < cursor)
    
    sessions = query.limit(limit + 1).all()
    
    next_cursor = None
    if len(sessions) > limit:
        next_cursor = sessions[limit].id
        sessions = sessions[:limit]
    
    return sessions, next_cursor


def list_archived_sessions(
    db: SQLSession, user_id: int, limit: int = 50, cursor: Optional[int] = None
) -> tuple[list[DBSession], Optional[int]]:
    """Fetch paginated archived sessions for a user, ordered by archive time (newest first)."""
    query = db.query(DBSession).filter(
        DBSession.user_id == user_id,
        DBSession.archived_at.isnot(None),
    ).order_by(DBSession.archived_at.desc())
    
    if cursor:
        query = query.filter(DBSession.id < cursor)
    
    sessions = query.limit(limit + 1).all()
    
    next_cursor = None
    if len(sessions) > limit:
        next_cursor = sessions[limit].id
        sessions = sessions[:limit]
    
    return sessions, next_cursor


def get_session_requests(
    db: SQLSession, session_id: int, limit: int = 50, cursor: Optional[int] = None,
    order: str = "desc",
) -> tuple[list[DBRequest], Optional[int]]:
    """Fetch paginated requests for a session, ordered by creation time.

    When cursor is provided, fetches older requests (for scrolling up).
    order: 'asc' for oldest first, 'desc' for newest first (default).
    """
    query = db.query(DBRequest).filter(DBRequest.session_id == session_id)
    query = query.order_by(
        DBRequest.created_at.asc() if order == "asc" else DBRequest.created_at.desc()
    )
    
    if cursor:
        if order == "asc":
            query = query.filter(DBRequest.id > cursor)
        else:
            query = query.filter(DBRequest.id < cursor)
    
    requests = query.limit(limit + 1).all()
    
    next_cursor = None
    if len(requests) > limit:
        next_cursor = requests[limit].id
        requests = requests[:limit]
    
    return requests, next_cursor
