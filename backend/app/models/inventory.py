"""
Inventory models for JM Baryani HQ.
Tracks stock levels, movements, and reorder points.
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func
import enum

from app.database import Base


class StockItem(Base):
    """Represents a trackable inventory item."""
    __tablename__ = "stock_items"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, index=True)
    description = Column(Text, nullable=True)

    # Categorization
    category = Column(String(20), default="lain")  # basah, kering, lain
    sub_category = Column(String(100), nullable=True)  # e.g., "daging", "rempah", "beras"

    # Units
    unit = Column(String(50), default="unit")  # kg, liter, pcs, packet, etc.

    # Stock levels
    current_stock = Column(Float, default=0.0)
    minimum_stock = Column(Float, default=0.0)  # Reorder point
    maximum_stock = Column(Float, nullable=True)  # Max capacity (optional)

    # Cost tracking
    last_unit_cost = Column(Float, default=0.0)  # Last purchase price per unit
    average_unit_cost = Column(Float, default=0.0)  # Weighted average cost

    # Usage patterns (calculated)
    avg_daily_usage = Column(Float, default=0.0)  # Rolling 7-day average
    days_of_stock = Column(Float, default=0.0)  # current_stock / avg_daily_usage

    # Status
    is_active = Column(Boolean, default=True)
    supplier_id = Column(Integer, ForeignKey("suppliers.id"), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    movements = relationship("StockMovement", back_populates="stock_item", cascade="all, delete-orphan")
    supplier = relationship("Supplier", backref="stock_items")


class StockMovement(Base):
    """Records every stock in/out movement."""
    __tablename__ = "stock_movements"

    id = Column(Integer, primary_key=True, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Movement type
    movement_type = Column(String(20), nullable=False)  # "in", "out", "adjustment", "waste"

    # Quantity (positive for in, negative for out)
    quantity = Column(Float, nullable=False)
    unit_cost = Column(Float, default=0.0)  # Cost per unit at time of movement
    total_cost = Column(Float, default=0.0)  # quantity * unit_cost

    # Reference to source
    reference_type = Column(String(50), nullable=True)  # "invoice", "sales", "manual", "waste"
    reference_id = Column(Integer, nullable=True)  # e.g., invoice_id

    # Details
    notes = Column(Text, nullable=True)
    performed_by = Column(String(100), nullable=True)

    # Stock snapshot after movement
    stock_after = Column(Float, default=0.0)

    # Timestamps
    movement_date = Column(DateTime(timezone=True), server_default=func.now())
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    stock_item = relationship("StockItem", back_populates="movements")


class ReorderAlert(Base):
    """Tracks reorder alerts for low stock items."""
    __tablename__ = "reorder_alerts"

    id = Column(Integer, primary_key=True, index=True)
    stock_item_id = Column(Integer, ForeignKey("stock_items.id"), nullable=False)

    # Alert details
    current_stock = Column(Float, default=0.0)
    minimum_stock = Column(Float, default=0.0)
    suggested_order_qty = Column(Float, default=0.0)  # Based on avg usage + lead time
    days_until_stockout = Column(Float, default=0.0)

    # Status
    status = Column(String(20), default="active")  # active, acknowledged, ordered, resolved
    acknowledged_at = Column(DateTime(timezone=True), nullable=True)
    resolved_at = Column(DateTime(timezone=True), nullable=True)

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    stock_item = relationship("StockItem", backref="alerts")
