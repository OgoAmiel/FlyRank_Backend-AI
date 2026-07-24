from contextlib import asynccontextmanager

from fastapi import FastAPI

from database import create_db_and_tables
from routes.tasks import router as task_router


@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
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