from datetime import date
from fastapi import HTTPException, status
from sqlalchemy.orm import Session as SQLSession

from app.models import User


def check_rate_limit(user: User, db: SQLSession) -> None:
    """Check if a user can make a request. Raises 403 if blocked."""
    if not user.is_guest:
        today = date.today()
        if user.daily_requests_date != today:
            user.daily_requests_used = 0
            user.daily_requests_date = today
            db.commit()

        if user.daily_requests_used >= User.DAILY_LIMIT:
            remaining = 0
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail={
                    "code": "daily_limit_reached",
                    "message": f"You've used all {User.DAILY_LIMIT} daily requests. Sign up or bring your own API key for unlimited use.",
                    "remaining": remaining,
                    "limit": User.DAILY_LIMIT,
                },
            )
        return

    # Guest check
    if user.requests_count >= User.GUEST_LIMIT:
        remaining = max(0, User.GUEST_LIMIT - user.requests_count)
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "code": "guest_limit_reached",
                "message": f"You've used all {User.GUEST_LIMIT} free requests. Create an account to continue generating models.",
                "remaining": remaining,
                "limit": User.GUEST_LIMIT,
            },
        )


def increment_request_count(user: User, db: SQLSession) -> None:
    """Increment request counters after a request is created."""
    user.requests_count = (user.requests_count or 0) + 1
    if not user.is_guest:
        today = date.today()
        if user.daily_requests_date != today:
            user.daily_requests_used = 0
            user.daily_requests_date = today
        user.daily_requests_used = (user.daily_requests_used or 0) + 1
    db.commit()


def get_fastapi_ip(request) -> str:
    """Extract client IP from request, respecting X-Forwarded-For."""
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "0.0.0.0"
