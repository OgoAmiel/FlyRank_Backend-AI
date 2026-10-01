import pytest

from main import app
from dependencies import get_task_service


class FakeTaskService:

    def get_all_tasks(self):
        return [
            {
                "id": 1,
                "title": "Test task",
                "done": False
            }
        ]

    def get_task_by_id(self, task_id):
        if task_id == 1:
            return {
                "id": 1,
                "title": "Test task",
                "done": False
            }

        return None

    def create_task(self, title):
        return {
            "id": 2,
            "title": title,
            "done": False
        }

    def update_task(self, task_id, title=None, done=None):
        if task_id != 1:
            return None

        return {
            "id": 1,
            "title": title if title is not None else "Test task",
            "done": done if done is not None else False
        }

    def delete_task(self, task_id):
        if task_id == 1:
            return True

        return False


@pytest.fixture(autouse=True)
def override_task_service():
    def get_fake_task_service():
        return FakeTaskService()

    app.dependency_overrides[get_task_service] = get_fake_task_service

    yield

    app.dependency_overrides.pop(get_task_service, None)


def test_get_tasks(client):
    response = client.get("/tasks/")

    assert response.status_code == 200
    assert isinstance(response.json(), list)

    assert response.json() == [
        {
            "id": 1,
            "title": "Test task",
            "done": False
        }
    ]


def test_get_task_by_id(client):
    response = client.get("/tasks/1")

    assert response.status_code == 200

    assert response.json() == {
        "id": 1,
        "title": "Test task",
        "done": False
    }

def test_get_task_not_found(client):
    response = client.get("/tasks/999")

    assert response.status_code == 404

    assert response.json() == {
        "error": "Task 999 not found"
    }

def test_create_task(client):
    response = client.post(
        "/tasks/",
        json={"title": "Learn automated testing"}
    )

    assert response.status_code == 201

    assert response.json() == {
        "id": 2,
        "title": "Learn automated testing",
        "done": False
    }


def test_create_task_with_blank_title(client):
    response = client.post(
        "/tasks/",
        json={"title": "   "}
    )

    assert response.status_code == 400

    assert response.json() == {
        "error": "Title is required"
    }

def test_update_task(client):
    response = client.put(
        "/tasks/1",
        json={
            "title": "Updated test task",
            "done": True
        }
    )

    assert response.status_code == 200

    assert response.json() == {
        "id": 1,
        "title": "Updated test task",
        "done": True
    }


def test_update_task_not_found(client):
    response = client.put(
        "/tasks/999",
        json={
            "title": "Updated task",
            "done": True
        }
    )

    assert response.status_code == 404

    assert response.json() == {
        "error": "Task 999 not found"
    }


def test_update_task_with_blank_title(client):
    response = client.put(
        "/tasks/1",
        json={
            "title": "   ",
            "done": True
        }
    )

    assert response.status_code == 400

    assert response.json() == {
        "error": "Title is required"
    }

def test_delete_task(client):
    response = client.delete("/tasks/1")

    assert response.status_code == 204
    assert response.content == b""


def test_delete_task_not_found(client):
    response = client.delete("/tasks/999")

    assert response.status_code == 404

    assert response.json() == {
        "error": "Task 999 not found"
    }

def test_create_task_without_title(client):
    response = client.post(
        "/tasks/",
        json={}
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Title is required"
    }