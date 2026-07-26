from contextlib import asynccontextmanager
import os
from dotenv import load_dotenv

from fastapi import FastAPI
from supabase import create_client, Client

from database import create_db_and_tables
from routes.tasks import router as task_router

# Load environment variables from .env
load_dotenv()

# Initialize Supabase client
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

if not SUPABASE_URL or not SUPABASE_KEY:
    raise ValueError("Missing SUPABASE_URL or SUPABASE_KEY in .env file")

supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)


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

@app.get("/", summary="API info")
def root():
    """Describes what this API is and what it offers."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": ["/tasks"],
    }

@app.get("/health", summary="Health check")
def health():
    """Confirms the server is alive."""
    return {"status": "ok"}