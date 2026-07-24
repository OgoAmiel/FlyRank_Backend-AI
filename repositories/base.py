from abc import ABC, abstractmethod
from models import Task


class TaskRepository(ABC):
    """
    Contract that every task repository must implement.
    """

    @abstractmethod
    def get_all_tasks(self) -> list[Task]:
        """Return all tasks."""
        pass

    @abstractmethod
    def get_task_by_id(self, task_id: int) -> Task | None:
        """Return one task or None."""
        pass

    @abstractmethod
    def create_task(self, title: str) -> Task:
        """Create and return a task."""
        pass

    @abstractmethod
    def update_task(
        self,
        task_id: int,
        title: str | None = None,
        done: bool | None = None,
    ) -> Task | None:
        """Update a task."""
        pass

    @abstractmethod
    def delete_task(self, task_id: int) -> bool:
        """Delete a task."""
        pass