from fastapi import APIRouter, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session as SQLSession

from app.db import get_db
from app.schemas import CreateRequestPayload, RequestCreatedResponse, RequestStatusResponse, RequestResult, StageInfo, TimestampsInfo
import app.services as services
from app.models import RequestStatus

router = APIRouter(prefix="/sessions", tags=["requests"])


@router.post("/{session_id}/requests", response_model=RequestCreatedResponse)
def submit_request(
    session_id: int,
    payload: CreateRequestPayload,
    background_tasks: BackgroundTasks,
    db: SQLSession = Depends(get_db),
):
    session = services.get_session(db, session_id)
    if not session:
        raise HTTPException(status_code=404, detail="Session not found")

    db_request = services.create_queued_request(db, session_id, payload.prompt)

    if not db_request.id:
        raise HTTPException(status_code=500, detail="Failed to create request")

    background_tasks.add_task(
        services.execute_request_background,
        db_request.id,
        session_id,
    )

    return RequestCreatedResponse(
        request_id=db_request.id,
        session_id=session_id,
        status=db_request.status.value,
        created_at=db_request.created_at,
    )


# Separate router for GET + retry endpoints under /requests prefix
requests_router = APIRouter(tags=["requests"])


@requests_router.get("/{request_id}", response_model=RequestStatusResponse)
def get_request_status(request_id: int, db: SQLSession = Depends(get_db)):
    db_request = services.get_request(db, request_id)
    if not db_request:
        raise HTTPException(status_code=404, detail="Request not found")

    stage = None
    if db_request.status not in (RequestStatus.COMPLETED, RequestStatus.FAILED):
        stage = StageInfo(
            name=db_request.current_stage,
            attempt=db_request.attempts,
            max_attempts=5,
            latest_code=db_request.code,
            latest_error=db_request.error,
        )

    result = None
    if db_request.status in (RequestStatus.COMPLETED, RequestStatus.FAILED):
        result = RequestResult(
            code=db_request.code,
            error=db_request.error,
            artifact_url=db_request.result_artifact_url,
            attempts=db_request.attempts,
            agent_state=db_request.agent_state,
        )

    return RequestStatusResponse(
        request_id=db_request.id,
        session_id=db_request.session_id,
        status=db_request.status.value,
        stage=stage,
        prompt=db_request.prompt,
        timestamps=TimestampsInfo(
            created_at=db_request.created_at,
            started_at=db_request.started_at,
            completed_at=db_request.completed_at,
        ),
        result=result,
    )


@requests_router.post("/{request_id}/retry", response_model=RequestCreatedResponse)
def retry_request(
    request_id: int,
    background_tasks: BackgroundTasks,
    db: SQLSession = Depends(get_db),
):
    original = services.get_request(db, request_id)
    if not original:
        raise HTTPException(status_code=404, detail="Request not found")
    if original.status != RequestStatus.FAILED:
        raise HTTPException(status_code=400, detail="Only failed requests can be retried")

    new_request = services.create_queued_request(db, original.session_id, original.prompt)

    background_tasks.add_task(
        services.execute_request_background,
        new_request.id,
        new_request.session_id,
    )

    return RequestCreatedResponse(
        request_id=new_request.id,
        session_id=new_request.session_id,
        status=new_request.status.value,
        created_at=new_request.created_at,
    )

