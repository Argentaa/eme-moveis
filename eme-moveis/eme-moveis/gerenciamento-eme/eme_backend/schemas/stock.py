from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from enum import Enum


class CategoryType(str, Enum):
    STOCK = "STOCK"
    FINANCIAL = "FINANCIAL"


class CategoryBase(BaseModel):
    name: str
    description: Optional[str] = None
    category_type: CategoryType = CategoryType.STOCK


class CategoryCreate(CategoryBase):
    pass


class CategoryUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None


class CategoryResponse(CategoryBase):
    id: str

    class Config:
        from_attributes = True


class StockItemBase(BaseModel):
    name: str
    sku: str
    category_id: str
    quantity: float
    min_quantity: float
    unit: str
    price: float
    supplier: str


class StockItemCreate(StockItemBase):
    pass


class StockItemUpdate(BaseModel):
    name: Optional[str] = None
    sku: Optional[str] = None
    category_id: Optional[str] = None
    quantity: Optional[float] = None
    min_quantity: Optional[float] = None
    unit: Optional[str] = None
    price: Optional[float] = None
    supplier: Optional[str] = None


class StockItemResponse(StockItemBase):
    id: str
    category_name: str

    class Config:
        from_attributes = True


class MovementType(str, Enum):
    ENTRADA = "ENTRADA"
    SAIDA = "SAIDA"


class StockMovementCreate(BaseModel):
    item_id: str
    type: MovementType
    quantity: float
    reason: str


class StockMovementResponse(BaseModel):
    id: str
    item_id: str
    item_name: str
    type: MovementType
    quantity: float
    reason: str
    created_by: str
    date: datetime

    class Config:
        from_attributes = True
