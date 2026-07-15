# Task API

A simple CRUD API built with FastAPI for managing a to-do list.
The application stores data in memory using a Python list, meaning all tasks are lost when the server is restarted.

---

## Technologies Used

- Python 3
- FastAPI
- Uvicorn

---

## Installation

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
```

---

## Running the Application

Start the development server:

```bash
uvicorn main:app --reload
```

The API will be available at:

```text
http://127.0.0.1:8000
```

Swagger documentation:

```text
http://127.0.0.1:8000/docs
```

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

### Create a new task

```powershell
Invoke-RestMethod `
    -Uri "http://127.0.0.1:8000/tasks" `
    -Method POST `
    -ContentType "application/json" `
    -Body '{"title":"Buy milk"}'
```

### Response

```json
{
    "id": 4,
    "title": "Buy milk",
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
http://127.0.0.1:8000/docs
```

to test the API directly from your browser.

Insert your Swagger screenshot below:

![Swagger Screenshot](images/swagger.png)

---

## Author

Ogorogile Madisa