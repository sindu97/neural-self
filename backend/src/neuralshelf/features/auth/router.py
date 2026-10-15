"""Authentication API endpoints."""

from typing import Annotated

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.orm import Session

from neuralshelf.core.config import get_settings
from neuralshelf.core.messages import Message, MessageCode
from neuralshelf.core.schemas import ApiResponse
from neuralshelf.db.session import get_db
from neuralshelf.features.auth.dependencies import get_current_user
from neuralshelf.features.auth.rate_limit import RateLimiter, client_ip
from neuralshelf.features.auth.schemas import (
    LoginRequest,
    RefreshTokenRequest,
    RevokeTokenRequest,
    SignupRequest,
)
from neuralshelf.features.auth.service import AuthService
from neuralshelf.features.users.models import User
from neuralshelf.features.users.schemas import UserResponse

router = APIRouter(prefix="/auth", tags=["Authentication"])

Db = Annotated[Session, Depends(get_db)]


@router.post(
    "/signup",
    response_model=ApiResponse[UserResponse],
    status_code=status.HTTP_201_CREATED,
)
def signup(payload: SignupRequest, request: Request, db: Db) -> ApiResponse[UserResponse]:
    """Register a new user account."""
    RateLimiter(db).hit(
        f"signup:ip:{client_ip(request)}", limit=get_settings().rate_limit_signup_per_ip
    )
    user = AuthService(db).signup(
        name=payload.name,
        email=str(payload.email).lower(),
        password=payload.password,
    )

    return ApiResponse[UserResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.SIGNUP_SUCCESSFUL,
        data=[UserResponse.model_validate(user)],
    )


@router.post("/login", response_model=ApiResponse)
def login(payload: LoginRequest, request: Request, db: Db) -> ApiResponse:
    """Authenticate a user and issue access and refresh tokens."""
    settings = get_settings()
    email = str(payload.email).lower()
    limiter = RateLimiter(db)
    # Per IP stops one client trying many accounts; per email stops many
    # clients guessing one account's password.
    limiter.hit(f"login:ip:{client_ip(request)}", limit=settings.rate_limit_login_per_ip)
    limiter.hit(f"login:email:{email}", limit=settings.rate_limit_login_per_email)

    result = AuthService(db).login(email=email, password=payload.password)

    return ApiResponse(
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.LOGIN_SUCCESSFUL,
        data=[result],
    )


@router.post("/refresh", response_model=ApiResponse)
def refresh(payload: RefreshTokenRequest, request: Request, db: Db) -> ApiResponse:
    """Exchange a refresh token for a new access and refresh token pair."""
    RateLimiter(db).hit(
        f"refresh:ip:{client_ip(request)}", limit=get_settings().rate_limit_refresh_per_ip
    )
    result = AuthService(db).refresh(refresh_token=payload.refresh_token)

    return ApiResponse(
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.TOKEN_REFRESHED,
        data=[result],
    )


@router.post("/revoke", response_model=ApiResponse)
def revoke(payload: RevokeTokenRequest, db: Db) -> ApiResponse:
    """Revoke a refresh token so it can no longer be used."""
    AuthService(db).revoke(refresh_token=payload.refresh_token)

    return ApiResponse(
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.TOKEN_REVOKED,
        data=[],
    )


@router.get("/me", response_model=ApiResponse[UserResponse])
def get_me(
    current_user: Annotated[User, Depends(get_current_user)],
) -> ApiResponse[UserResponse]:
    """Return the authenticated user's public profile."""
    return ApiResponse[UserResponse](
        success=True,
        code=MessageCode.SUCCESS,
        message=Message.PROFILE_RETRIEVED,
        data=[UserResponse.model_validate(current_user)],
    )
