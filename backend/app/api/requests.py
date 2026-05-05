from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session as SQLSession

from app.db import get_db
from app.schemas import CreateRequestPayload, RequestCreatedResponse, RequestStatusResponse, RequestResult
import app.services as services

router = APIRouter(prefix="/sessions", tags=["requests"])


@router.post("/{session_id}/request", response_model=RequestCreatedResponse)
def submit_request(
    session_id: int,
    payload: CreateRequestPayload,
    background_tasks: BackgroundTasks,
    db: SQLSession = Depends(get_db),
):
    """Submit a new prompt for a session. Returns immediately with QUEUED status."""
    session = services.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")
    
    # Create request with QUEUED status
    db_request = services.create_queued_request(db, session_id, payload.prompt)
    
    # Ensure request ID is properly set
    if not db_request.id:
        raise HTTPException(status_code=500, detail="Failed to create request")
    
    # Queue background execution
    background_tasks.add_task(
        services.execute_request_background,
        db_request.id,
        session_id,
    )
    
    return RequestCreatedResponse(
        request_id=db_request.id,
        status=db_request.status.value,
        created_at=db_request.created_at,
    )


# Separate router for the GET endpoint since it has a different path structure
status_router = APIRouter(tags=["requests"])


@status_router.get("/request/{request_id}", response_model=RequestStatusResponse)
def get_request_status(request_id: int, db: SQLSession = Depends(get_db)):
    """Poll a request for status and result."""
    db_request = services.get_request(db, request_id)
    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")
    
    result = None
    if db_request.status.value in ["completed", "failed"]:
        result = RequestResult(
            code=db_request.code,
            error=db_request.error,
            result_artifact_url=db_request.result_artifact_url,
            attempts=db_request.attempts,
            agent_state=db_request.agent_state,
        )
    
    return RequestStatusResponse(
        request_id=db_request.id,
        session_id=db_request.session_id,
        status=db_request.status.value,
        current_stage=db_request.current_stage,
        prompt=db_request.prompt,
        created_at=db_request.created_at,
        started_at=db_request.started_at,
        completed_at=db_request.completed_at,
        result=result,
    )
    

