import os
from datetime import datetime
from typing import Optional
from sqlalchemy.orm import Session as SQLSession
import cadquery as cq

from app.models import Request as DBRequest, RequestStatus
from app.agent.graph import app as agent_graph
from app.agent.state import AgentState
from .session_service import get_session_requests
from app.utils import now


ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "/tmp/cad_artifacts")


def ensure_artifacts_dir():
    """Ensure artifacts directory exists."""
    os.makedirs(ARTIFACTS_DIR, exist_ok=True)


def export_stl(result: Optional[object], request_id: int) -> Optional[str]:
    """Export CadQuery result to STL file and return the serving URL."""
    if result is None:
        return None
    
    ensure_artifacts_dir()
    stl_filename = f"request_{request_id}.stl"
    stl_path = os.path.join(ARTIFACTS_DIR, stl_filename)
    try:
        cq.exporters.export(result, stl_path)
        # Return URL instead of path
        artifacts_base_url = os.environ.get("ARTIFACTS_BASE_URL", "http://localhost:8000")
        return f"{artifacts_base_url}/artifacts/{stl_filename}"
    except Exception as e:
        print(f"Failed to export STL for request {request_id}: {e}")
        return None


def hydrate_agent_state(db: SQLSession, session_id: int) -> AgentState:
    """Load session context and build an AgentState for the agent graph."""
    from .session_service import get_session
    
    session = get_session(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")
    
    # Fetch prior requests in this session to extract prompt history
    requests, _ = get_session_requests(db, session_id, limit=1000)
    
    prompt_history = [req.prompt for req in requests][::-1]
    latest_request = requests[-1] if requests else None
    
    # Extract last successful code from agent_state if available
    latest_code = ""
    if latest_request and latest_request.agent_state:
        latest_code = latest_request.agent_state.get("code", "")
    
    # Start fresh state but carry forward prompt history and code style
    state: AgentState = {
        "latest_prompt": "",  # Will be set by the caller
        "prompt_history": prompt_history,
        "mode": "refine" if requests else "initial",
        "iteration": len(requests) + 1,
        "plan": "",
        "code": latest_code,  # Use prior code for style consistency in refine mode
        "error": None,
        "fix_history": [],
        "attempts": 0,
        "result": None,
    }
    
    return state


def create_queued_request(db: SQLSession, session_id: int, prompt: str) -> DBRequest:
    """
    Create a request record with QUEUED status.
    Returns immediately without executing the agent.
    """
    from .session_service import get_session
    
    session = get_session(db, session_id)
    if not session:
        raise ValueError(f"Session {session_id} not found")
    
    # Create request record with QUEUED status
    db_request = DBRequest(
        session_id=session_id,
        prompt=prompt,
        status=RequestStatus.QUEUED,
        created_at=now(),
    )
    db.add(db_request)
    db.commit()
    db.refresh(db_request)
    
    return db_request


def execute_request_background(request_id: int, session_id: int) -> None:
    """
    Background worker: execute agent and persist results.
    Should be called via BackgroundTasks or threading.
    """
    from app.db import SessionLocal
    from .session_service import get_session
    
    db = SessionLocal()
    try:
        db_request = get_request(db, request_id)
        if not db_request:
            print(f"Request {request_id} not found")
            return
        
        session = get_session(db, session_id)
        if not session:
            print(f"Session {session_id} not found")
            return
        
        # Mark as RUNNING
        db_request.status = RequestStatus.RUNNING
        db_request.started_at = now()
        db.commit()
        
        try:
            # Hydrate state from prior session context
            state = hydrate_agent_state(db, session_id)
            state["latest_prompt"] = db_request.prompt
            
            # Run the agent graph
            result_state = agent_graph.invoke(state)
            
            # Store full agent state (plan, fix_history, mode, iteration, etc.)
            # This allows schema to evolve without migrations
            agent_state_to_store = {
                "plan": result_state.get("plan", ""),
                "fix_history": result_state.get("fix_history", []),
                "mode": result_state.get("mode", ""),
                "iteration": result_state.get("iteration", 0),
                "latest_prompt": result_state.get("latest_prompt", ""),
                "prompt_history": result_state.get("prompt_history", []),
            }
            
            # Extract key outputs for direct columns
            code = result_state.get("code", "")
            error = result_state.get("error")
            result = result_state.get("result")
            attempts = result_state.get("attempts", 0)
            
            # Export artifact if successful
            artifact_path = None
            if result:
                artifact_path = export_stl(result, db_request.id)
            
            # Format error info as dict
            error_dict = None
            if error:
                try:
                    error_dict = {
                        "type": error.error_type if hasattr(error, "error_type") else type(error).__name__,
                        "message": error.message if hasattr(error, "message") else str(error),
                        "traceback": str(error) if hasattr(error, "traceback") else "",
                    }
                except Exception:
                    error_dict = {
                        "type": type(error).__name__,
                        "message": str(error),
                    }
            
            # Update request with results
            db_request.status = RequestStatus.COMPLETED if error is None else RequestStatus.FAILED
            db_request.completed_at = now()
            db_request.code = code
            db_request.error = error_dict
            db_request.attempts = attempts
            db_request.result_artifact_url = artifact_path
            db_request.agent_state = agent_state_to_store
            db.commit()
            
        except Exception as e:
            # Catch and persist any execution errors
            db_request.status = RequestStatus.FAILED
            db_request.completed_at = now()
            db_request.error = {
                "type": type(e).__name__,
                "message": str(e),
            }
            db.commit()
        
        # Update session timestamp
        session.updated_at = now()
        db.commit()
    
    finally:
        db.close()


def execute_request(db: SQLSession, session_id: int, prompt: str) -> DBRequest:
    """
    Legacy function: create request and queue background execution.
    Use create_queued_request() + background tasks in API layer instead.
    """
    db_request = create_queued_request(db, session_id, prompt)
    # Note: actual execution should be queued via BackgroundTasks in API layer
    return db_request


def get_request(db: SQLSession, request_id: int) -> Optional[DBRequest]:
    """Fetch a request by ID."""
    return db.query(DBRequest).filter(DBRequest.id == request_id).first()
