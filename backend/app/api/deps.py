from fastapi import Header, HTTPException, status, Depends
from sqlalchemy.orm import Session as SQLSession

from app.db import get_db
from app.models import User
from app.services.auth_service import decode_jwt


async def get_current_user(
    authorization: str | None = Header(None),
    db: SQLSession = Depends(get_db),
) -> User:
    """FastAPI dependency: validates Bearer JWT and returns the User."""
    if authorization is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Authorization header",
        )
    scheme, _, token = authorization.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authorization scheme",
        )
    try:
        user_id = decode_jwt(token)
    except Exception as e:
        detail = "Token expired" if "expired" in str(e).lower() else "Invalid token"
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=detail,
        )

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="User not found",
        )
    return user
