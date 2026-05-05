from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey
from sqlalchemy.orm import relationship
from .base import Base
from app.utils import now


class Session(Base):
    __tablename__ = "sessions"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    title = Column(String(255), nullable=True)
    archived_at = Column(DateTime, nullable=True, default=None)  # None = active, timestamp = archived
    created_at = Column(DateTime, default=now, nullable=False)
    updated_at = Column(DateTime, default=now, onupdate=now, nullable=False)

    user = relationship("User", back_populates="sessions")
    requests = relationship("Request", back_populates="session", cascade="all, delete-orphan")

    @property
    def is_active(self) -> bool:
        """Check if session is active (not archived)."""
        return self.archived_at is None

    def __repr__(self):
        return f"<Session(id={self.id}, user_id={self.user_id}, is_active={self.is_active})>"
