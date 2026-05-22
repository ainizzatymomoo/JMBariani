from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


# --- Stock Item Schemas ---

class StockItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    category: str = "lain"
    sub_category: Optional[str] = None
    unit: str = "unit"
    minimum_stock: float = 0.0
    maximum_stock: Optional[float] = None
    supplier_id: Optional[int] = None


class StockItemCreate(StockItemBase):
    current_stock: float = 0.0


class StockItemUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    category: Optional[str] = None
    sub_category: Optional[str] = None
    unit: Optional[str] = None
    minimum_stock: Optional[float] = None
    maximum_stock: Optional[float] = None
    current_stock: Optional[float] = None
    supplier_id: Optional[int] = None
    is_active: Optional[bool] = None


class StockItemResponse(StockItemBase):
    id: int
    current_stock: float
    last_unit_cost: float
    average_unit_cost: float
    avg_daily_usage: float
    days_of_stock: float
    is_active: bool
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class StockItemSummary(BaseModel):
    """Lightweight stock item for list views."""
    id: int
    name: str
    category: str
    unit: str
    current_stock: float
    minimum_stock: float
    days_of_stock: float
    is_low_stock: bool = False

    class Config:
        from_attributes = True


# --- Stock Movement Schemas ---

class StockMovementCreate(BaseModel):
    stock_item_id: int
    movement_type: str  # "in", "out", "adjustment", "waste"
    quantity: float
    unit_cost: Optional[float] = 0.0
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    notes: Optional[str] = None


class StockMovementResponse(BaseModel):
    id: int
    stock_item_id: int
    movement_type: str
    quantity: float
    unit_cost: float
    total_cost: float
    reference_type: Optional[str] = None
    reference_id: Optional[int] = None
    notes: Optional[str] = None
    stock_after: float
    movement_date: Optional[datetime] = None

    class Config:
        from_attributes = True


# --- Reorder Alert Schemas ---

class ReorderAlertResponse(BaseModel):
    id: int
    stock_item_id: int
    current_stock: float
    minimum_stock: float
    suggested_order_qty: float
    days_until_stockout: float
    status: str
    created_at: Optional[datetime] = None
    stock_item: Optional[StockItemSummary] = None

    class Config:
        from_attributes = True


# --- Dashboard Summary ---

class InventorySummary(BaseModel):
    total_items: int
    total_value: float
    low_stock_count: int
    basah_items: int
    kering_items: int
    active_alerts: int
