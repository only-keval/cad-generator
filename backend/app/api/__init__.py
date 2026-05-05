import os
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from ..db import init_db
from ..agent.rag import build_retriever
from .users import router as users_router
from .sessions import router as sessions_router
from .requests import router as requests_router, status_router as status_router

app = FastAPI(title="CAD Generator API", version="0.1.0")


# Startup event: initialize database
@app.on_event("startup")
async def startup_event():
    init_db()
    build_retriever()


# Include routers
app.include_router(users_router)
app.include_router(sessions_router)
app.include_router(requests_router)
app.include_router(status_router)


@app.get("/health")
def health():
    """Health check endpoint."""
    return {"status": "ok"}


# Mount artifacts directory for serving generated STL files
ARTIFACTS_DIR = os.environ.get("ARTIFACTS_DIR", "/tmp/cad_artifacts")
os.makedirs(ARTIFACTS_DIR, exist_ok=True)  # Ensure directory exists before mounting
app.mount("/artifacts", StaticFiles(directory=ARTIFACTS_DIR), name="artifacts")
