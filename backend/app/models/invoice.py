from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Enum, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class ItemCategory(str, enum.Enum):
    BASAH = "basah"       # Wet goods: meat, vegetables, dairy
    KERING = "kering"     # Dry goods: rice, spices, oil
    LAIN = "lain"         # Others: packaging, cleaning, etc.


class InvoiceStatus(str, enum.Enum):
    PENDING = "pending"           # Uploaded, awaiting OCR
    PARSED = "parsed"             # OCR done, awaiting review
    VERIFIED = "verified"         # Manually verified/corrected
    REJECTED = "rejected"         # Invalid/duplicate


class Supplier(Base):
    __tablename__ = "suppliers"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    phone = Column(String(50), nullable=True)
    email = Column(String(255), nullable=True)
    address = Column(Text, nullable=True)
    category = Column(String(50), nullable=True)  # e.g., "meat", "spices", "vegetables"
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    invoices = relationship("Invoice", back_populates="supplier")


class Invoice(Base):
    __tablename__ = "invoices"

    id = Column(Integer, primary_key=True, index=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Invoice metadata
    invoice_number = Column(String(100), nullable=True)
    invoice_date = Column(DateTime(timezone=True), nullable=True)
    received_date = Column(DateTime(timezone=True), server_default=func.now())

    # Financial
    subtotal = Column(Float, default=0.0)
    tax = Column(Float, default=0.0)
    total = Column(Float, default=0.0)

    # Status & Processing
    status = Column(String(20), default=InvoiceStatus.PENDING.value)
    ocr_raw_text = Column(Text, nullable=True)  # Raw OCR output for reference
    ocr_confidence = Column(Float, nullable=True)  # OCR confidence score 0-100

    # File info
    original_filename = Column(String(255), nullable=True)
    file_path = Column(String(500), nullable=True)
    file_type = Column(String(20), nullable=True)  # pdf, jpg, png

    # Category
    category = Column(String(20), default=ItemCategory.LAIN.value)

    # Audit
    notes = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    supplier = relationship("Supplier", back_populates="invoices")
    items = relationship("InvoiceItem", back_populates="invoice", cascade="all, delete-orphan")


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id = Column(Integer, primary_key=True, index=True)
    invoice_id = Column(Integer, ForeignKey("invoices.id"), nullable=False)

    # Item details
    name = Column(String(255), nullable=False)
    description = Column(Text, nullable=True)
    quantity = Column(Float, default=0.0)
    unit = Column(String(50), nullable=True)  # kg, pcs, liter, packet, etc.
    unit_price = Column(Float, default=0.0)
    total_price = Column(Float, default=0.0)

    # Categorization
    category = Column(String(20), default=ItemCategory.LAIN.value)

    # Relationships
    invoice = relationship("Invoice", back_populates="items")
