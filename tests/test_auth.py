from types import SimpleNamespace

import routes.auth as auth_routes


class FakeSupabaseAuth:
    def sign_up(self, credentials):
        return SimpleNamespace(
            user={
                "id": "test-user-123",
                "email": credentials["email"]
            }
        )


class FakeSupabase:
    def __init__(self):
        self.auth = FakeSupabaseAuth()


class FakeSupabaseAuthError:
    def sign_up(self):
        raise Exception("Supabase signup failed")


class FakeSupabaseError:
    def __init__(self):
        self.auth = FakeSupabaseAuthError()

class FakeSupabaseAuthLogin:
    def sign_in_with_password(self, credentials):
        return SimpleNamespace(
            session=SimpleNamespace(
                access_token="fake-access-token",
                refresh_token="fake-refresh-token"
            )
        )

class FakeSupabaseAuthInvalidLogin:
    def sign_in_with_password(self, credentials):
        return SimpleNamespace(session=None)

class FakeSupabaseAuthLoginError:
    def sign_in_with_password(self, credentials):
        raise Exception("Supabase login failed")


def test_signup_success(client, monkeypatch):
    fake_supabase = FakeSupabase()

    monkeypatch.setattr(
        auth_routes,
        "supabase",
        fake_supabase
    )

    response = client.post(
        "/auth/signup",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 201
    assert response.json() == {
        "id": "test-user-123",
        "email": "test@example.com"
    }

def test_signup_missing_email(client):
    response = client.post(
        "/auth/signup",
        json={
            "email": "",
            "password": "password123"
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Email and password are required"
    }

def test_signup_missing_password(client):
    response = client.post(
        "/auth/signup",
        json={
            "email": "test@example.com",
            "password": ""
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Email and password are required"
    }

def test_signup_supabase_error(client, monkeypatch):
    fake_supabase = FakeSupabaseError()

    monkeypatch.setattr(
        auth_routes,
        "supabase",
        fake_supabase
    )

    response = client.post(
        "/auth/signup",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Unable to create account"
    }


def test_login_success(client, monkeypatch):
    fake_supabase = SimpleNamespace(
        auth=FakeSupabaseAuthLogin()
    )

    monkeypatch.setattr(
        auth_routes,
        "supabase",
        fake_supabase
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 200
    assert response.json() == {
        "access_token": "fake-access-token",
        "refresh_token": "fake-refresh-token"
    }

def test_login_invalid_credentials(client, monkeypatch):
    fake_supabase = SimpleNamespace(
        auth=FakeSupabaseAuthInvalidLogin()
    )

    monkeypatch.setattr(
        auth_routes,
        "supabase",
        fake_supabase
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "wrongpassword"
        }
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": "Invalid login credentials"
    }

def test_login_supabase_error(client, monkeypatch):
    fake_supabase = SimpleNamespace(
        auth=FakeSupabaseAuthLoginError()
    )

    monkeypatch.setattr(
        auth_routes,
        "supabase",
        fake_supabase
    )

    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": "password123"
        }
    )

    assert response.status_code == 401
    assert response.json() == {
        "error": "Invalid login credentials"
    }

def test_login_missing_email(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "",
            "password": "password123"
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Email and password are required"
    }

def test_login_missing_password(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com",
            "password": ""
        }
    )

    assert response.status_code == 400
    assert response.json() == {
        "error": "Email and password are required"
    }

def test_login_without_password_field(client):
    response = client.post(
        "/auth/login",
        json={
            "email": "test@example.com"
        }
    )

    assert response.status_code == 422