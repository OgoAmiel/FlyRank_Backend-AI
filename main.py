from fastapi import FastAPI, HTTPException

app = FastAPI()

tasks = [
    {
        "id": 1,
        "title": "Learn FastAPI",
        "done": False
    },
    {
        "id": 2,
        "title": "Build CRUD API",
        "done": True
    },
    {
        "id": 3,
        "title": "Submit assignment",
        "done": False
    }
]

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
def get_tasks():
    """Returns the list of all tasks."""
    return tasks


@app.get("/tasks/{task_id}", summary="Get a specific task")
def get_task(task_id: int):
    """Returns a specific task by its ID."""
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail=f"Task {task_id} not found")