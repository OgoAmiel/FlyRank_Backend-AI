from sqlmodel import SQLModel, Session, create_engine, select
from models import Task

# SQLite database file
DATABASE_URL = "sqlite:///tasks.db"

# Create the database engine
engine = create_engine(
    DATABASE_URL,
    echo=True,
    connect_args={"check_same_thread": False}
)


def create_db_and_tables():
    """Create database tables and seed initial data if empty."""
    SQLModel.metadata.create_all(engine)

    with Session(engine) as session:
        # Check if there are already tasks in the database
        existing_task = session.exec(select(Task)).first()

        if existing_task is None:
            sample_tasks = [
                Task(title="Learn FastAPI", done=False),
                Task(title="Build CRUD API", done=False),
                Task(title="Submit assignment", done=False),
            ]

            session.add_all(sample_tasks)
            session.commit()


def get_session():
    """Provide a database session."""
    with Session(engine) as session:
        yield session