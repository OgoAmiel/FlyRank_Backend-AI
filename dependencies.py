from repositories.postgres_repository import PostgresRepository
from services.task_service import TaskService

repository = PostgresRepository()
service = TaskService(repository)

def get_task_service():
    return service