import os
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from ..db import init_db, SessionLocal
from ..models import RequestStatus
from ..utils import now
from ..agent.rag import build_retriever
from ..auth import get_current_user
from .users import router as users_router
from .sessions import router as sessions_router
from .requests import router as requests_submit_router, requests_router
from .auth import router as auth_router

app = FastAPI(title="CAD Generator API", version="0.1.0")

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    init_db()
    build_retriever()

    db = SessionLocal()
    try:
        from ..models import Request
        stuck = db.query(Request).filter(Request.status == RequestStatus.RUNNING).all()
        for req in stuck:
            req.status = RequestStatus.FAILED
            req.current_stage = None
            req.completed_at = now()
            req.error = {"type": "ServerRestart", "message": "Server restarted while request was running"}
        if stuck:
            db.commit()
            print(f"[recovery] Marked {len(stuck)} stuck requests as FAILED")
    finally:
        db.close()


# Auth router is public (no JWT required)
app.include_router(auth_router)

# All other routes require JWT
_auth = [Depends(get_current_user)]
app.include_router(users_router, dependencies=_auth)
app.include_router(sessions_router, dependencies=_auth)
app.include_router(requests_submit_router, dependencies=_auth)
app.include_router(requests_router, prefix="/requests", dependencies=_auth)


@app.get("/health")
def health():
    return {"status": "ok"}


ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "/tmp/cad_artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")
