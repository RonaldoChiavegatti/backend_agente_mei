import uuid

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer


_auth_scheme = HTTPBearer(auto_error=False)


def get_current_user_id(
    credentials: HTTPAuthorizationCredentials = Depends(_auth_scheme),
) -> uuid.UUID:
    """Extract the current user id from a bearer token.

    The lightweight implementation expects the token payload to be a raw UUID.
    It is intentionally simple so that tests can override the dependency with
    deterministic values.
    """

    if credentials is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authorization credentials were not provided.",
        )

    try:
        return uuid.UUID(credentials.credentials)
    except (ValueError, AttributeError) as exc:  # pragma: no cover - defensive
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid authentication token.",
        ) from exc

