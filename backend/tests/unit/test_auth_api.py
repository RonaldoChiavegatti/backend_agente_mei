import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient

# Allow imports from the project
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.auth_service.application.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from services.auth_service.infrastructure.security import get_current_user_id
from services.auth_service.infrastructure.web import api
from shared.models.base_models import User as UserResponse
from shared.models.base_models import Token


class FakeUserService:
    def __init__(
        self,
        user: UserResponse | None = None,
        raise_not_found: bool = False,
        raise_conflict: bool = False,
        raise_invalid_credentials: bool = False,
        token: Token | None = None,
    ):
        self.user = user
        self.raise_not_found = raise_not_found
        self.raise_conflict = raise_conflict
        self.raise_invalid_credentials = raise_invalid_credentials
        self.token = token

    def register_user(self, *args, **kwargs) -> UserResponse:
        if self.raise_conflict:
            raise UserAlreadyExistsError("User already exists")
        assert self.user is not None
        return self.user

    def login(self, *args, **kwargs) -> Token:
        if self.raise_invalid_credentials:
            raise InvalidCredentialsError("Invalid credentials")
        assert self.token is not None
        return self.token

    def get_user_profile(self, user_id: uuid.UUID) -> UserResponse:
        if self.raise_not_found or self.user is None:
            raise UserNotFoundError("User not found")
        return self.user


class TestAuthProfileEndpoint(unittest.TestCase):
    def setUp(self):
        self.app = FastAPI()
        self.app.include_router(api.router)
        self.client = TestClient(self.app)
        self.user_id = uuid.uuid4()

    def tearDown(self):
        self.app.dependency_overrides = {}

    def test_profile_endpoint_returns_email_and_created_at(self):
        timestamp = datetime.now(timezone.utc)
        user = UserResponse(
            id=self.user_id,
            full_name="Test User",
            email="test@example.com",
            created_at=timestamp,
            updated_at=timestamp,
        )

        self.app.dependency_overrides[api.get_user_service] = lambda: FakeUserService(
            user=user
        )
        self.app.dependency_overrides[get_current_user_id] = lambda: self.user_id

        response = self.client.get("/auth/profile")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["email"], "test@example.com")
        returned_timestamp = datetime.fromisoformat(
            payload["created_at"].replace("Z", "+00:00")
        )
        self.assertEqual(returned_timestamp, timestamp)

    def test_profile_endpoint_returns_404_when_user_missing(self):
        self.app.dependency_overrides[api.get_user_service] = lambda: FakeUserService(
            raise_not_found=True
        )
        self.app.dependency_overrides[get_current_user_id] = lambda: self.user_id

        response = self.client.get("/auth/profile")

        self.assertEqual(response.status_code, 404)
        self.assertEqual(response.json()["detail"], "User not found")

    def test_register_endpoint_returns_created_user_payload(self):
        timestamp = datetime.now(timezone.utc)
        user = UserResponse(
            id=self.user_id,
            full_name="New User",
            email="new@example.com",
            created_at=timestamp,
            updated_at=timestamp,
        )

        self.app.dependency_overrides[api.get_user_service] = lambda: FakeUserService(
            user=user
        )

        response = self.client.post(
            "/auth/register",
            json={
                "full_name": "New User",
                "email": "new@example.com",
                "password": "s3cret",
            },
        )

        self.assertEqual(response.status_code, 201)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.user_id))
        self.assertEqual(payload["email"], "new@example.com")
        self.assertEqual(payload["full_name"], "New User")

    def test_register_endpoint_returns_409_on_conflict(self):
        self.app.dependency_overrides[api.get_user_service] = lambda: FakeUserService(
            raise_conflict=True
        )

        response = self.client.post(
            "/auth/register",
            json={
                "full_name": "Existing User",
                "email": "existing@example.com",
                "password": "password",
            },
        )

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()["detail"], "User already exists")

    def test_register_endpoint_rejects_empty_password(self):
        response = self.client.post(
            "/auth/register",
            json={
                "full_name": "Empty Password",
                "email": "empty@example.com",
                "password": " ",
            },
        )

        self.assertEqual(response.status_code, 422)
        self.assertEqual(response.json()["detail"], "Password cannot be empty.")

    def test_login_endpoint_returns_access_token_payload(self):
        token = Token(access_token="token-123", token_type="bearer")
        self.app.dependency_overrides[api.get_user_service] = lambda: FakeUserService(
            token=token
        )

        response = self.client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "password"},
        )

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {"access_token": "token-123", "token_type": "bearer"})

    def test_login_endpoint_returns_401_with_invalid_credentials(self):
        self.app.dependency_overrides[api.get_user_service] = lambda: FakeUserService(
            raise_invalid_credentials=True
        )

        response = self.client.post(
            "/auth/login",
            data={"username": "test@example.com", "password": "wrong"},
        )

        self.assertEqual(response.status_code, 401)
        self.assertEqual(response.json()["detail"], "Invalid credentials")

    def test_login_token_allows_access_to_profile(self):
        timestamp = datetime.now(timezone.utc)
        user = UserResponse(
            id=self.user_id,
            full_name="Test User",
            email="user@example.com",
            created_at=timestamp,
            updated_at=timestamp,
        )
        token = Token(access_token=str(self.user_id), token_type="bearer")
        self.app.dependency_overrides[api.get_user_service] = lambda: FakeUserService(
            user=user, token=token
        )

        login_response = self.client.post(
            "/auth/login",
            data={"username": "user@example.com", "password": "password"},
        )

        self.assertEqual(login_response.status_code, 200)
        access_token = login_response.json()["access_token"]

        profile_response = self.client.get(
            "/auth/profile", headers={"Authorization": f"Bearer {access_token}"}
        )

        self.assertEqual(profile_response.status_code, 200)
        self.assertEqual(profile_response.json()["email"], "user@example.com")

    def test_me_endpoint_returns_full_user_payload(self):
        timestamp = datetime.now(timezone.utc)
        user = UserResponse(
            id=self.user_id,
            full_name="Test User",
            email="me@example.com",
            created_at=timestamp,
            updated_at=timestamp,
        )

        self.app.dependency_overrides[api.get_user_service] = lambda: FakeUserService(
            user=user
        )
        self.app.dependency_overrides[get_current_user_id] = lambda: self.user_id

        response = self.client.get("/auth/me")

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["id"], str(self.user_id))
        self.assertEqual(payload["email"], "me@example.com")
        self.assertEqual(payload["full_name"], "Test User")


if __name__ == "__main__":
    unittest.main()
