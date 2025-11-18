import uuid

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from services.auth_service.application.exceptions import (
    InvalidCredentialsError,
    UserAlreadyExistsError,
    UserNotFoundError,
)
from services.auth_service.application.ports.input.user_service import UserService
from services.auth_service.infrastructure.dependencies import get_user_service
from services.auth_service.infrastructure.security import get_current_user_id
from shared.models.base_models import Token, UserCreate, UserProfile
from shared.models.base_models import User as UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED
)
def register_user_endpoint(
    user_create: UserCreate, user_service: UserService = Depends(get_user_service)
):
    if not user_create.password.strip():
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Password cannot be empty.",
        )
    try:
        user = user_service.register_user(
            full_name=user_create.full_name,
            email=user_create.email,
            password=user_create.password,
        )
        return user
    except UserAlreadyExistsError as e:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/me", response_model=UserResponse)
def get_current_user_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    try:
        return user_service.get_user_profile(user_id=user_id)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.get("/profile", response_model=UserProfile)
def get_basic_user_profile(
    user_id: uuid.UUID = Depends(get_current_user_id),
    user_service: UserService = Depends(get_user_service),
):
    """
    Returns the authenticated user's basic profile data (email and signup date).
    """
    try:
        user = user_service.get_user_profile(user_id=user_id)
        return UserProfile(email=user.email, created_at=user.created_at)
    except UserNotFoundError as e:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=str(e))
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )


@router.post("/login", response_model=Token)
def login_for_access_token_endpoint(
    form_data: OAuth2PasswordRequestForm = Depends(),
    user_service: UserService = Depends(get_user_service),
):
    try:
        # OAuth2 uses 'username' field for the email
        token = user_service.login(
            email=form_data.username, password=form_data.password
        )
        return token
    except InvalidCredentialsError as e:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
            headers={"WWW-Authenticate": "Bearer"},
        )
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Internal server error",
        )
