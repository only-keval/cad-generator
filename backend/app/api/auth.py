from fastapi import APIRouter, Depends, HTTPException, status, Request as FastAPIRequest
from sqlalchemy.orm import Session as SQLSession

from app.db import get_db
from app.models import User
from app.schemas.auth import (
    SignupPayload, LoginPayload, AuthResponse,
    MigratePayload, UserInfoResponse, LimitInfoResponse,
)
from app.services.auth_service import hash_password, verify_password, create_jwt
from app.api.deps import get_current_user
from app.services.rate_limit import get_fastapi_ip
from app.utils import now
from datetime import date

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
def create_guest(request: FastAPIRequest, db: SQLSession = Depends(get_db)):
    ip = get_fastapi_ip(request)

    existing = db.query(User).filter(User.ip_address == ip, User.is_guest == True).first()
    if existing:
        token = create_jwt(existing.id)
        return AuthResponse(
            token=token, user_id=existing.id,
            name=existing.name, is_guest=True,
        )

    import uuid
    guest_id = str(uuid.uuid4())[:8]
    name = f"Guest {guest_id}"
    user = User(name=name, is_guest=True, ip_address=ip)
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
    user.ip_address = None
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


@router.get("/limits", response_model=LimitInfoResponse)
def get_limits(
    user: User = Depends(get_current_user),
    db: SQLSession = Depends(get_db),
):
    if user.is_guest:
        used = user.requests_count or 0
        limit = User.GUEST_LIMIT
        remaining = max(0, limit - used)
        return LimitInfoResponse(
            is_guest=True, requests_used=used,
            requests_remaining=remaining, limit=limit,
            limit_type="guest_total",
        )
    else:
        today = date.today()
        if user.daily_requests_date != today:
            used = 0
        else:
            used = user.daily_requests_used or 0
        limit = User.DAILY_LIMIT
        remaining = max(0, limit - used)
        return LimitInfoResponse(
            is_guest=False, requests_used=used,
            requests_remaining=remaining, limit=limit,
            limit_type="daily",
        )
