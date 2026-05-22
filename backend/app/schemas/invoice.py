from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime


class InvoiceItemBase(BaseModel):
    name: str
    description: Optional[str] = None
    quantity: float = 0.0
    unit: Optional[str] = None
    unit_price: float = 0.0
    total_price: float = 0.0
    category: str = "lain"


class InvoiceItemCreate(InvoiceItemBase):
    pass


class InvoiceItemResponse(InvoiceItemBase):
    id: int
    invoice_id: int

    class Config:
        from_attributes = True


class SupplierBase(BaseModel):
    name: str
    phone: Optional[str] = None
    email: Optional[str] = None
    address: Optional[str] = None
    category: Optional[str] = None
    notes: Optional[str] = None


class SupplierCreate(SupplierBase):
    pass


class SupplierResponse(SupplierBase):
    id: int
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class InvoiceBase(BaseModel):
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    subtotal: float = 0.0
    tax: float = 0.0
    total: float = 0.0
    category: str = "lain"
    notes: Optional[str] = None


class InvoiceUpdate(BaseModel):
    """For manual correction after OCR."""
    supplier_name: Optional[str] = None
    invoice_number: Optional[str] = None
    invoice_date: Optional[datetime] = None
    subtotal: Optional[float] = None
    tax: Optional[float] = None
    total: Optional[float] = None
    category: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    items: Optional[List[InvoiceItemCreate]] = None


class InvoiceResponse(InvoiceBase):
    id: int
    supplier_id: Optional[int] = None
    status: str
    ocr_confidence: Optional[float] = None
    original_filename: Optional[str] = None
    file_path: Optional[str] = None
    file_type: Optional[str] = None
    ocr_raw_text: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    items: List[InvoiceItemResponse] = []
    supplier: Optional[SupplierResponse] = None

    class Config:
        from_attributes = True


class OCRResultResponse(BaseModel):
    """Response after OCR processing."""
    invoice_id: int
    status: str
    ocr_confidence: float
    parsed_data: dict
    message: str
