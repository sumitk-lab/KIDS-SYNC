"""Authentication endpoints (Register, Login, Me)."""

from fastapi import APIRouter, Depends, Request, status
from sqlalchemy.ext.asyncio import AsyncSession

from src.api.deps import get_client_ip, get_current_user, get_db
from src.models.user import UserModel
from src.schemas.common import ApiResponse
from src.schemas.user import TokenResponse, UserCreate, UserLogin, UserResponse
from src.services.user_service import UserService

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post(
    "/register",
    response_model=ApiResponse[TokenResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Register a new user account",
)
async def register(
    data: UserCreate,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    """Register a new guardian, caregiver, or administrator account."""
    client_ip = get_client_ip(request)
    service = UserService(db)
    _, tokens = await service.register_user(data, client_ip=client_ip)
    return ApiResponse(
        success=True,
        message="User account registered successfully.",
        data=tokens,
    )


@router.post(
    "/login",
    response_model=ApiResponse[TokenResponse],
    summary="Authenticate with email and password",
)
async def login(
    data: UserLogin,
    request: Request,
    db: AsyncSession = Depends(get_db),
) -> ApiResponse[TokenResponse]:
    """Authenticate with credentials and obtain JWT tokens."""
    client_ip = get_client_ip(request)
    service = UserService(db)
    _, tokens = await service.authenticate(
        email=data.email,
        password=data.password,
        client_ip=client_ip,
    )
    return ApiResponse(
        success=True,
        message="Authentication successful.",
        data=tokens,
    )


@router.get(
    "/me",
    response_model=ApiResponse[UserResponse],
    summary="Get current authenticated user profile",
)
async def get_me(
    current_user: UserModel = Depends(get_current_user),
) -> ApiResponse[UserResponse]:
    """Fetch profile data for the authenticated session."""
    user_dto = UserResponse.model_validate(current_user)
    return ApiResponse(
        success=True,
        message="Current user profile retrieved.",
        data=user_dto,
    )
