from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session as SQLSession

from app.db import get_db
from app.models import User
from app.schemas import CreateUserPayload, UserResponse
import app.services as services

router = APIRouter(prefix="/users", tags=["users"])


@router.post("", response_model=UserResponse)
def create_user(payload: CreateUserPayload, db: SQLSession = Depends(get_db)):
    """Create a new user."""
    user = services.create_user(db, name=payload.name, email=payload.email)
    return UserResponse(user_id=user.id, name=user.name, email=user.email, created_at=user.created_at)


@router.get("/{user_id}", response_model=UserResponse)
def get_user(user_id: int, db: SQLSession = Depends(get_db)):
    """Fetch user info."""
    user = services.get_user(db, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    return UserResponse(user_id=user.id, name=user.name, email=user.email, created_at=user.created_at)
