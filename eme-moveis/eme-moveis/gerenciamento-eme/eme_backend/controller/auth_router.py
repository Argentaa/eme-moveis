from fastapi import APIRouter, Depends, Request

from endpoints.rate_limiter import limiter
from endpoints.security import get_current_user, require_roles
from schemas.user import (
    LoginRequest,
    LoginResponse,
    UserCreate,
    UserResponse,
    UserUpdateRole,
    TokenData,
)
from service.auth_service import auth_service

router = APIRouter(prefix="/api/auth", tags=["Auth"])

@router.post("/login", response_model=LoginResponse)
@limiter.limit("5/minute")
async def login(request: Request, data: LoginRequest) -> LoginResponse:
    return await auth_service.login(data.username, data.password)


@router.get("/me", response_model=UserResponse)
async def me(current_user: TokenData = Depends(get_current_user)) -> UserResponse:
    return await auth_service.me(current_user.user_id)


@router.get(
    "/users",
    response_model=list[UserResponse],
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def get_users() -> list[UserResponse]:
    return await auth_service.get_users()


@router.post(
    "/users",
    response_model=UserResponse,
    status_code=201,
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def create_user(data: UserCreate) -> UserResponse:
    return await auth_service.create_user(data)


@router.put(
    "/users/{user_id}/role",
    response_model=UserResponse,
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def update_user_role(user_id: str, data: UserUpdateRole) -> UserResponse:
    return await auth_service.update_user_role(user_id, data.role.value)


@router.delete(
    "/users/{user_id}",
    dependencies=[Depends(require_roles("ADMIN"))],
)
async def delete_user(
    user_id: str,
    current_user: TokenData = Depends(get_current_user),
) -> dict:
    return await auth_service.delete_user(user_id, current_user.user_id)
