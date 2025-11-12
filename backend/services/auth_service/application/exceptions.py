class ApplicationError(Exception):
    """Base class for application-level exceptions."""

    pass


class UserAlreadyExistsError(ApplicationError):
    """Raised when trying to register a user that already exists."""

    pass


class InvalidCredentialsError(ApplicationError):
    """Raised when login credentials are invalid."""

    pass


class UserNotFoundError(ApplicationError):
    """Raised when the requested user does not exist."""

    pass
