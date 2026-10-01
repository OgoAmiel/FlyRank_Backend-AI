import pytest
from fastapi.testclient import TestClient

from main import app


@pytest.fixture
def client():
    """
    Creates a TestClient without triggering the application's
    database startup lifecycle.
    """
    test_client = TestClient(app)

    yield test_client

    app.dependency_overrides.clear()