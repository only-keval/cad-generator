from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean
from sqlalchemy.orm import relationship
from .base import Base
from app.utils import now


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=True, index=True)
    password_hash = Column(String(255), nullable=True)
    is_guest = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=now, nullable=False)

    sessions = relationship("Session", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, name={self.name}, guest={self.is_guest})>"
