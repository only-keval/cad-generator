from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Text, ForeignKey, Enum, JSON
from sqlalchemy.orm import relationship
import enum
from .base import Base
from app.utils import now


class RequestStatus(str, enum.Enum):
    QUEUED = "queued"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class Request(Base):
    __tablename__ = "requests"

    id = Column(Integer, primary_key=True)
    session_id = Column(Integer, ForeignKey("sessions.id"), nullable=False)
    
    # Input
    prompt = Column(Text, nullable=False)
    
    # Status
    status = Column(Enum(RequestStatus), default=RequestStatus.QUEUED, nullable=False)
    created_at = Column(DateTime, default=now, nullable=False)
    started_at = Column(DateTime, nullable=True)
    completed_at = Column(DateTime, nullable=True)
    
    # Results - key outputs stored as direct columns
    code = Column(Text, nullable=True)
    error = Column(JSON, nullable=True)  # error details {type, message, traceback}
    result_artifact_url = Column(String(512), nullable=True)  # URL to exported STL
    attempts = Column(Integer, default=0, nullable=False)
    
    # Full agent state (plan, fix_history, mode, iteration, etc.) stored as JSON
    # This allows schema to evolve as agent logic changes without requiring migrations
    agent_state = Column(JSON, nullable=True, default=dict)
    
    session = relationship("Session", back_populates="requests")

    def __repr__(self):
        return f"<Request(id={self.id}, session_id={self.session_id}, status={self.status})>"
