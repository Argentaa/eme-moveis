from pydantic import BaseModel
from typing import Optional
from datetime import date, datetime
from enum import Enum


class ProjectStatus(str, Enum):
    ORCAMENTO = "ORCAMENTO"
    PROJETADO = "PROJETADO"
    PRODUCAO = "PRODUCAO"
    MONTAGEM = "MONTAGEM"
    CONCLUIDO = "CONCLUIDO"


class ProjectStep(BaseModel):
    id: str
    label: str
    completed: bool


class ProjectBase(BaseModel):
    title: str
    client_id: str
    description: str
    status: ProjectStatus
    value: float
    deadline: date
    steps: list[ProjectStep]


class ProjectCreate(ProjectBase):
    pass


class ProjectUpdate(BaseModel):
    title: Optional[str] = None
    client_id: Optional[str] = None
    description: Optional[str] = None
    status: Optional[ProjectStatus] = None
    value: Optional[float] = None
    deadline: Optional[date] = None


class ProjectStepsUpdate(BaseModel):
    steps: list[ProjectStep]


class ProjectResponse(ProjectBase):
    id: str
    client_name: str
    created_at: datetime

    class Config:
        from_attributes = True
