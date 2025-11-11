from pydantic import EmailStr
from services.auth_service.application.domain.user import User as DomainUser
from services.auth_service.application.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
)
from services.auth_service.application.ports.input.user_service import UserService
from services.auth_service.application.ports.output.password_hasher import (
    PasswordHasher,
)
from services.auth_service.application.ports.output.token_provider import TokenProvider
from services.auth_service.application.ports.output.user_repository import (
    UserRepository,
)
from shared.models.base_models import Token
from shared.models.base_models import User as UserResponse


class UserServiceImpl(UserService):
    """
    Concrete implementation of the UserService input port.
    Orchestrates the business logic for user registration and login.
    """

    def __init__(
        self,
        user_repository: UserRepository,
        password_hasher: PasswordHasher,
        token_provider: TokenProvider,
    ):
        self.user_repository = user_repository
        self.password_hasher = password_hasher
        self.token_provider = token_provider

    def register_user(
        self, full_name: str, email: EmailStr, password: str
    ) -> UserResponse:
        """
        Handles the business logic for user registration.
        1. Checks if a user with the given email already exists.
        2. Hashes the password.
        3. Creates a new user domain entity.
        4. Saves the new user via the repository.
        5. Returns a user response DTO.
        """
        if self.user_repository.get_by_email(email):
            raise UserAlreadyExistsError(f"User with email {email} already exists.")

        hashed_password = self.password_hasher.hash(password)

        new_user = DomainUser(
            full_name=full_name,
            email=email,
            hashed_password=hashed_password,
        )

        saved_user = self.user_repository.save(new_user)

        return UserResponse.model_validate(saved_user, from_attributes=True)

    def login(self, email: EmailStr, password: str) -> Token:
        """
        Handles the business logic for user login.
        1. Retrieves the user by email.
        2. Verifies the password.
        3. Creates a JWT access token.
        4. Returns the token.
        """
        user = self.user_repository.get_by_email(email)
        if not user:
            raise InvalidCredentialsError("Invalid email or password.")

        if not self.password_hasher.verify(password, user.hashed_password):
            raise InvalidCredentialsError("Invalid email or password.")

        access_token = self.token_provider.create_access_token(
            data={"sub": str(user.id), "email": user.email}
        )

        return Token(access_token=access_token, token_type="bearer")
