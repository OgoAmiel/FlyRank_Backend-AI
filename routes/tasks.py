from fastapi import APIRouter, HTTPException, Depends

from schemas import TaskCreate, TaskUpdate
from dependencies import get_task_service
from services.task_service import TaskService


router = APIRouter(
    prefix="/tasks",
    tags=["Tasks"]
)

@router.get("/", summary="Get all tasks")
def get_tasks(service: TaskService = Depends(get_task_service)):
    """Returns all tasks."""
    return service.get_all_tasks()

@router.get("/{task_id}", summary="Get a specific task")
def get_task(task_id: int, service: TaskService = Depends(get_task_service)):
    """Returns a task by its ID."""
    task = service.get_task_by_id(task_id)

    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task

@router.post("/", status_code=201, summary="Create a new task")
def create_task(task: TaskCreate, service: TaskService = Depends(get_task_service)):
    """Creates a new task with the provided title."""

    if not task.title or not task.title.strip():
        raise HTTPException(status_code=400, detail="Title is required")
    return service.create_task(task.title)

@router.put("/{task_id}", summary="Update a task")
def update_task(task_id: int, updated_task: TaskUpdate, service: TaskService = Depends(get_task_service)):
    """Updates an existing task."""

    if (updated_task.title is not None and not updated_task.title.strip()):
        raise HTTPException(status_code=400, detail="Title is required")

    task = service.update_task(
        task_id=task_id,
        title=updated_task.title,
        done=updated_task.done,
    )

    if task is None:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")
    return task

@router.delete("/{task_id}", status_code=204, summary="Delete a task")
def delete_task(task_id: int, service: TaskService = Depends(get_task_service)):
    """Deletes a task."""

    deleted = service.delete_task(task_id)

    if not deleted:
        raise HTTPException(status_code=404, detail=f"Task {task_id} not found")