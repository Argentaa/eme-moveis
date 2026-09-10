from datetime import datetime, timedelta, timezone

import bcrypt
import jwt
from fastapi import HTTPException, status

from config import settings
from repo.user_repo import user_repo
from schemas.user import UserCreate, UserResponse, LoginResponse, TokenData


class AuthService:
    """Lógica de autenticação: login, criação de usuários, JWT."""

    def _hash_password(self, password: str) -> str:
        return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")

    def _verify_password(self, plain: str, hashed: str) -> bool:
        return bcrypt.checkpw(plain.encode("utf-8"), hashed.encode("utf-8"))

    def _create_access_token(self, data: dict) -> str:
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + timedelta(
            minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES
        )
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

    def decode_token(self, token: str) -> TokenData:
        try:
            payload = jwt.decode(
                token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM]
            )
            user_id: str = payload.get("sub", "")
            username: str = payload.get("username", "")
            role: str = payload.get("role", "")
            if not user_id:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Token inválido",
                )
            return TokenData(user_id=user_id, username=username, role=role)
        except jwt.ExpiredSignatureError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token expirado",
            )
        except jwt.InvalidTokenError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token inválido",
            )

    async def login(self, username: str, password: str) -> LoginResponse:
        user = await user_repo.find_by_username(username)
        if user is None or not self._verify_password(password, user["password"]):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Usuário ou senha inválidos",
            )

        token = self._create_access_token(
            {"sub": user["id"], "username": user["username"], "role": user["role"]}
        )
        user_response = UserResponse(
            id=user["id"],
            username=user["username"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            avatar=user.get("avatar"),
        )
        return LoginResponse(token=token, user=user_response)

    async def me(self, user_id: str) -> UserResponse:
        user = await user_repo.find_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        return UserResponse(
            id=user["id"],
            username=user["username"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            avatar=user.get("avatar"),
        )

    async def get_users(self) -> list[UserResponse]:
        rows = await user_repo.find_all()
        return [UserResponse(**r) for r in rows]

    async def create_user(self, data: UserCreate) -> UserResponse:
        existing = await user_repo.find_by_username(data.username)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Username já existe",
            )
        existing_email = await user_repo.find_by_email(data.email)
        if existing_email:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="E-mail já cadastrado",
            )
        hashed = self._hash_password(data.password)
        user = await user_repo.create(
            username=data.username,
            name=data.name,
            email=data.email,
            role=data.role.value,
            hashed_password=hashed,
            avatar=data.avatar,
        )
        return UserResponse(**user)

    async def update_user_role(self, user_id: str, role: str) -> UserResponse:
        current = await user_repo.find_by_id(user_id)
        if current is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        if current["role"] == role:
            return UserResponse(
                id=current["id"],
                username=current["username"],
                name=current["name"],
                email=current["email"],
                role=current["role"],
                avatar=current.get("avatar"),
            )

        updated = await user_repo.update_role(user_id, role)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        user = await user_repo.find_by_id(user_id)
        if user is None:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        return UserResponse(
            id=user["id"],
            username=user["username"],
            name=user["name"],
            email=user["email"],
            role=user["role"],
            avatar=user.get("avatar"),
        )

    async def delete_user(self, user_id: str, current_user_id: str) -> dict:
        if user_id == current_user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Você não pode excluir sua própria conta",
            )
        deleted = await user_repo.delete(user_id)
        if not deleted:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Usuário não encontrado",
            )
        return {"message": "Usuário removido com sucesso"}


auth_service = AuthService()
