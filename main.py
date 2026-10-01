from contextlib import asynccontextmanager

from dotenv import load_dotenv
from fastapi import FastAPI

from database import create_db_and_tables
from routes.tasks import router as task_router
from routes.auth import router as auth_router
from routes.protected import router as protected_router
from routes.triage import router as triage_router


load_dotenv()


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    print("✓ Database initialized")
    print("✓ Supabase client initialized")

    yield


app = FastAPI(title="FlyRank Backend & AI", version="1.0", lifespan=lifespan)

app.include_router(task_router)
app.include_router(auth_router)
app.include_router(protected_router)
app.include_router(triage_router)

@app.get("/", summary="API info")
def root():
    """Describes what this API is and what it offers."""
    return {
        "name": "Task API",
        "version": "1.0",
        "endpoints": [
            "/tasks",
            "/auth/signup",
            "/auth/login",
            "/auth/logout",
            "/public/info",
            "/protected/profile",
            "/protected/dashboard",
            "/triage"
        ],
    }

@app.get("/health", summary="Health check")
def health():
    """Confirms the server is alive."""
    return {"status": "ok"}