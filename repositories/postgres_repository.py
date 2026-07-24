from sqlmodel import Session, select

from database import engine
from models import Task
from repositories.base import TaskRepository


class PostgresRepository(TaskRepository):
    """
    SQLite implementation of the TaskRepository contract.
    """

    def get_all_tasks(self) -> list[Task]:
        with Session(engine) as session:
            return session.exec(select(Task)).all()

    def get_task_by_id(self, task_id: int) -> Task | None:
        with Session(engine) as session:
            return session.get(Task, task_id)

    def create_task(self, title: str) -> Task:
        with Session(engine) as session:
            task = Task(title=title, done=False)

            session.add(task)
            session.commit()
            session.refresh(task)

            return task

    def update_task(
        self,
        task_id: int,
        title: str | None = None,
        done: bool | None = None,
    ) -> Task | None:

        with Session(engine) as session:

            task = session.get(Task, task_id)

            if task is None:
                return None

            if title is not None:
                task.title = title

            if done is not None:
                task.done = done

            session.add(task)
            session.commit()
            session.refresh(task)

            return task

    def delete_task(self, task_id: int) -> bool:

        with Session(engine) as session:

            task = session.get(Task, task_id)

            if task is None:
                return False

            session.delete(task)
            session.commit()

            return True