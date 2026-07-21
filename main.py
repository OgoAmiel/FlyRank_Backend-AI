from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException, Depends
from sqlmodel import Session, select
from pydantic import BaseModel

from database import create_db_and_tables, get_session
from models import Task

@asynccontextmanager
async def lifespan(app: FastAPI):
    create_db_and_tables()
    yield


app = FastAPI(lifespan=lifespan)

class TaskCreate(BaseModel):
    title: str = None

class TaskUpdate(BaseModel):
    title: str | None = None
    done: bool | None = None


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


@app.get("/tasks", summary="Get all tasks")
def get_tasks(session: Session = Depends(get_session)):
    """Returns the list of all tasks."""
    return session.exec(select(Task)).all()


@app.get("/tasks/{task_id}", summary="Get a specific task")
def get_task(task_id: int, session: Session = Depends(get_session)):
    """Returns a specific task by its ID."""
    task = session.get(Task, task_id)
    if not task:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task


@app.post("/tasks", status_code=201, summary="Create a new task")
def create_task(task: TaskCreate):
    """Creates a new task with the provided title."""
    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")

    new_task = {
        "id": len(tasks) + 1,
        "title": task.title,
        "done": False
    }

    tasks.append(new_task)
    return new_task


@app.put("/tasks/{task_id}", summary="Update an existing task")
def update_task(task_id: int, updated_task: TaskUpdate):
    """Updates an existing task with the provided title and/or done status."""
    for task in tasks:
        if task["id"] == task_id:

            if updated_task.title is not None:
                if not updated_task.title.strip():
                    raise HTTPException(status_code=400, detail="Title is required")

                task["title"] = updated_task.title

            if updated_task.done is not None:
                task["done"] = updated_task.done

            return task

    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")


@app.delete("/tasks/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int):
    """Deletes a specific task by its ID."""
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return {"message": f"Task {task_id} deleted successfully"}
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")