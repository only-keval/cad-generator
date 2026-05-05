"""
FastAPI application entry point for the CAD Generator backend.
Run with: uvicorn app.main:app --reload
"""
import os
from dotenv import load_dotenv

if not load_dotenv():
    print("WARNING: .env not found, assuming env vars are already set.")

from .api import app

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
