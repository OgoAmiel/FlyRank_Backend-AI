# ToDo List App

This ToDo List is a RESTful backend application developed with **FastAPI** and **SQLModel** that allows users to perform full CRUD (Create, Read, Update and Delete) operations on tasks.

---

## Technologies Used

| Technology | Purpose |
|------------|---------|
| Python | Programming Language |
| FastAPI | REST API Framework |
| SQLModel | ORM |
| SQLAlchemy | Database Engine |
| SQLite | Database |
| Uvicorn | ASGI Server |

---

## Installation

Clone the repository

```bash
git clone https://github.com/OgoAmiel/FlyRank_Backend-AI
```

Navigate into the project

```bash
cd todo_list
```

Create a virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment:

### Windows

```bash
venv\Scripts\activate
```

Install dependencies:

```bash
pip install fastapi uvicorn
pip install -r requirements.txt
pip install sqlmodel
```

---

## Running the Application

Start the development server:

```bash
uvicorn main:app --reload
```

The application will be available at

```
http://127.0.0.1:8000/tasks
```

Swagger UI

```
http://127.0.0.1:8000/docs#/
```
---

## Database

The project uses **SQLite** together with **SQLModel**.

The database file

```
tasks.db
```

is automatically created when the application starts.

If the database is empty, three sample tasks are inserted automatically.

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API information |
| GET | `/health` | Health check endpoint |
| GET | `/tasks` | Retrieve all tasks |
| GET | `/tasks/{id}` | Retrieve a specific task |
| POST | `/tasks` | Create a new task |
| PUT | `/tasks/{id}` | Update an existing task |
| DELETE | `/tasks/{id}` | Delete a task |

---

## Example Request

### Create a Task

```http
POST /tasks
```

Request

```json
{
    "title": "Write a Song"
}
```

Response

```json
{
    "id": 5,
    "title": "Write a Song",
    "done": false
}
```

---

## Example Tasks

When the server starts, it contains three example tasks:

```json
[
    {
        "id": 1,
        "title": "Learn FastAPI",
        "done": false
    },
    {
        "id": 2,
        "title": "Build CRUD API",
        "done": false
    },
    {
        "id": 3,
        "title": "Submit assignment",
        "done": false
    }
]
```

---

## Swagger UI

FastAPI automatically generates interactive API documentation.

Open:

```text
http://127.0.0.1:8000/docs#/
```

to test the API directly from your browser.

Swagger Screenshot Below

![Swagger Screenshot](images/swagger.png)

---

# 🗄 Example SQL Queries

Retrieve all tasks

```sql
SELECT * FROM tasks;
```

Completed tasks

```sql
SELECT * FROM tasks WHERE done = 1;
```

Count tasks

```sql
SELECT COUNT(*) FROM tasks;
```

# 🗃 Database

> SQLite database viewed using DB Browser for SQLite.

![Database](images/database-view.png)


## Author

Ogorogile Madisa