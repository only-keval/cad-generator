from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime
from sqlalchemy.orm import relationship
from .base import Base
from app.utils import now


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=now, nullable=False)

    sessions = relationship("Session", back_populates="user")

    def __repr__(self):
        return f"<User(id={self.id}, email={self.email})>"
