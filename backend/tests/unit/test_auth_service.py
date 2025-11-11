import sys
import unittest
import uuid
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock

# Add the project root to the system path to allow imports from services
project_root = Path(__file__).parent.parent.parent
sys.path.insert(0, str(project_root))

from services.auth_service.application.domain.user import User as DomainUser
from services.auth_service.application.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from services.auth_service.application.ports.output.password_hasher import (
    PasswordHasher,
)
from services.auth_service.application.ports.output.token_provider import TokenProvider
from services.auth_service.application.ports.output.user_repository import (
    UserRepository,
)
from services.auth_service.application.services.user_service_impl import UserServiceImpl


class TestUserService(unittest.TestCase):
    def setUp(self):
        # Create mocks for the output ports
        self.mock_user_repo = MagicMock(spec=UserRepository)
        self.mock_password_hasher = MagicMock(spec=PasswordHasher)
        self.mock_token_provider = MagicMock(spec=TokenProvider)

        # Instantiate the service with the mocks
        self.user_service = UserServiceImpl(
            user_repository=self.mock_user_repo,
            password_hasher=self.mock_password_hasher,
            token_provider=self.mock_token_provider,
        )

        # Common test data
        timestamp = datetime.now(timezone.utc)
        self.test_user_domain = DomainUser(
            id=uuid.uuid4(),
            full_name="Test User",
            email="test@example.com",
            hashed_password="hashed_password",
            created_at=timestamp,
            updated_at=timestamp,
        )

    def test_register_user_success(self):
        # Arrange
        self.mock_user_repo.get_by_email.return_value = None
        self.mock_password_hasher.hash.return_value = "hashed_password"
        self.mock_user_repo.save.return_value = self.test_user_domain

        # Act
        result = self.user_service.register_user(
            full_name="Test User", email="test@example.com", password="plain_password"
        )

        # Assert
        self.mock_user_repo.get_by_email.assert_called_once_with("test@example.com")
        self.mock_password_hasher.hash.assert_called_once_with("plain_password")
        self.mock_user_repo.save.assert_called_once()
        self.assertEqual(result.email, self.test_user_domain.email)

    def test_register_user_already_exists(self):
        # Arrange
        self.mock_user_repo.get_by_email.return_value = self.test_user_domain

        # Act & Assert
        with self.assertRaises(UserAlreadyExistsError):
            self.user_service.register_user(
                full_name="Test User",
                email="test@example.com",
                password="plain_password",
            )
        self.mock_user_repo.get_by_email.assert_called_once_with("test@example.com")
        self.mock_password_hasher.hash.assert_not_called()

    def test_login_success(self):
        # Arrange
        self.mock_user_repo.get_by_email.return_value = self.test_user_domain
        self.mock_password_hasher.verify.return_value = True
        self.mock_token_provider.create_access_token.return_value = "test_token"

        # Act
        result = self.user_service.login(
            email="test@example.com", password="correct_password"
        )

        # Assert
        self.mock_user_repo.get_by_email.assert_called_once_with("test@example.com")
        self.mock_password_hasher.verify.assert_called_once_with(
            "correct_password", "hashed_password"
        )
        self.mock_token_provider.create_access_token.assert_called_once_with(
            data={
                "sub": str(self.test_user_domain.id),
                "email": "test@example.com",
            }
        )
        self.assertEqual(result.access_token, "test_token")

    def test_login_user_not_found(self):
        # Arrange
        self.mock_user_repo.get_by_email.return_value = None

        # Act & Assert
        with self.assertRaises(InvalidCredentialsError):
            self.user_service.login(
                email="nonexistent@example.com", password="password"
            )
        self.mock_user_repo.get_by_email.assert_called_once_with(
            "nonexistent@example.com"
        )
        self.mock_password_hasher.verify.assert_not_called()

    def test_login_invalid_password(self):
        # Arrange
        self.mock_user_repo.get_by_email.return_value = self.test_user_domain
        self.mock_password_hasher.verify.return_value = False

        # Act & Assert
        with self.assertRaises(InvalidCredentialsError):
            self.user_service.login(email="test@example.com", password="wrong_password")
        self.mock_password_hasher.verify.assert_called_once_with(
            "wrong_password", "hashed_password"
        )
        self.mock_token_provider.create_access_token.assert_not_called()


if __name__ == "__main__":
    unittest.main()
