from models import Task
from repositories.base import TaskRepository


class TaskService:
    def __init__(self, repository: TaskRepository):
        self.repository = repository

    def get_all_tasks(self) -> list[Task]:
        """Return all tasks."""
        return self.repository.get_all_tasks()

    def get_task_by_id(self, task_id: int) -> Task | None:
        """Return one task or None."""
        return self.repository.get_task_by_id(task_id)

    def create_task(self, title: str) -> Task:
        """Create and return a task."""
        return self.repository.create_task(title)

    def update_task(self, task_id: int, title: str | None = None, done: bool | None = None) -> Task | None:
        """Update a task."""
        return self.repository.update_task(task_id, title, done)

    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        return self.repository.delete_task(task_id)