from pydantic import BaseModel, EmailStr, field_validator
from typing import Optional
from enum import Enum


class UserRole(str, Enum):
    ADMIN = "ADMIN"
    GERENTE = "GERENTE"
    ESTOQUE = "ESTOQUE"
    PROJETISTA = "PROJETISTA"


class UserBase(BaseModel):
    username: str
    name: str
    email: EmailStr
    role: UserRole
    avatar: Optional[str] = None


class UserCreate(UserBase):
    password: str

    @field_validator("password")
    @classmethod
    def password_min_length(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("A senha deve ter no mínimo 8 caracteres")
        return v


class UserUpdateRole(BaseModel):
    role: UserRole


class UserResponse(UserBase):
    id: str

    class Config:
        from_attributes = True


class LoginRequest(BaseModel):
    username: str
    password: str


class LoginResponse(BaseModel):
    token: str
    user: UserResponse


class TokenData(BaseModel):
    user_id: str
    username: str
    role: str
