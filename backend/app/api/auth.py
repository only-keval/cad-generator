from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session as SQLSession

from app.db import get_db
from app.models import User
from app.schemas.auth import (
    SignupPayload, LoginPayload, AuthResponse,
    MigratePayload, UserInfoResponse,
)
from app.auth import hash_password, verify_password, create_jwt, get_current_user
from app.utils import now

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/signup", response_model=AuthResponse)
def signup(payload: SignupPayload, db: SQLSession = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user = User(
        name=payload.name,
        email=payload.email,
        password_hash=hash_password(payload.password),
        is_guest=False,
    )
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_jwt(user.id)
    return AuthResponse(token=token, user_id=user.id, name=user.name, email=user.email, is_guest=False)


@router.post("/login", response_model=AuthResponse)
def login(payload: LoginPayload, db: SQLSession = Depends(get_db)):
    user = db.query(User).filter(User.email == payload.email).first()
    if not user or not user.password_hash:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")
    if not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid email or password")

    token = create_jwt(user.id)
    return AuthResponse(token=token, user_id=user.id, name=user.name, email=user.email, is_guest=user.is_guest)


@router.post("/guest", response_model=AuthResponse)
def create_guest(db: SQLSession = Depends(get_db)):
    import uuid
    guest_id = str(uuid.uuid4())[:8]
    name = f"Guest {guest_id}"
    user = User(name=name, is_guest=True)
    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_jwt(user.id)
    return AuthResponse(token=token, user_id=user.id, name=user.name, is_guest=True)


@router.post("/migrate", response_model=AuthResponse)
def migrate_account(
    payload: MigratePayload,
    db: SQLSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not user.is_guest:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Account is already registered")

    existing = db.query(User).filter(User.email == payload.email).first()
    if existing and existing.id != user.id:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail="Email already registered")

    user.name = payload.name
    user.email = payload.email
    user.password_hash = hash_password(payload.password)
    user.is_guest = False
    db.commit()
    db.refresh(user)

    token = create_jwt(user.id)
    return AuthResponse(token=token, user_id=user.id, name=user.name, email=user.email, is_guest=False)


@router.get("/me", response_model=UserInfoResponse)
def get_me(user: User = Depends(get_current_user)):
    return UserInfoResponse(
        user_id=user.id,
        name=user.name,
        email=user.email,
        is_guest=user.is_guest,
        created_at=user.created_at,
    )
