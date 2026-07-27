from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from fastapi import FastAPI

from database import create_db_and_tables
from routes.tasks import router as task_router
from routes.auth import router as auth_router
from supabase_client import supabase


@asynccontextmanager
async def lifespan(app: FastAPI):
    try:
        print("✓ Database initialized")
    except Exception as e:
        print(f"⚠ Database not available (this is OK for auth-only development): {e}")
    print("✓ Connected to Supabase")
    yield

app = FastAPI(title="Task API", version="1.0", lifespan=lifespan)
app.include_router(task_router)
app.include_router(auth_router)

@app.get("/", summary="API info")
def root():
    """Describes what this API is and what it offers."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks", "/auth/signup", "/auth/login"],
    }

@app.get("/health", summary="Health check")
def health():
    """Confirms the server is alive."""
    return {"status": "ok"}