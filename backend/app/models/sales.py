"""
Sales models for JM Baryani HQ.
Stores parsed data from uploaded sales reports (POS exports, manual reports).
"""

from sqlalchemy import Column, Integer, String, Float, DateTime, ForeignKey, Text, Date, Boolean
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class SalesReport(Base):
    """Represents an uploaded sales report file."""
    __tablename__ = "sales_reports"

    id = Column(Integer, primary_key=True, index=True)

    # File info
    original_filename = Column(String(255), nullable=False)
    file_path = Column(String(500), nullable=True)
    report_type = Column(String(50), nullable=False)  # daily_sales, fc_gp, delivery, ytd_sales, delivery_partner

    # Report metadata
    report_month = Column(String(20), nullable=True)  # e.g., "April 2026"
    report_year = Column(Integer, nullable=True)
    period_start = Column(Date, nullable=True)
    period_end = Column(Date, nullable=True)

    # Status
    status = Column(String(20), default="uploaded")  # uploaded, parsed, error

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())

    # Relationships
    daily_sales = relationship("DailySales", back_populates="report", cascade="all, delete-orphan")
    outlet_monthly = relationship("OutletMonthlySales", back_populates="report", cascade="all, delete-orphan")
    delivery_sales = relationship("DeliverySales", back_populates="report", cascade="all, delete-orphan")


class DailySales(Base):
    """Daily sales breakdown by outlet and channel."""
    __tablename__ = "daily_sales"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("sales_reports.id"), nullable=False)

    # Identity
    date = Column(Date, nullable=False, index=True)
    outlet = Column(String(100), nullable=False, index=True)

    # Sales by channel
    dine_in = Column(Float, default=0.0)
    takeaway = Column(Float, default=0.0)
    delivery = Column(Float, default=0.0)
    catering = Column(Float, default=0.0)
    service_charge = Column(Float, default=0.0)
    sst = Column(Float, default=0.0)
    total_sales = Column(Float, default=0.0)

    # Transaction count
    transaction_count = Column(Integer, default=0)

    # Relationships
    report = relationship("SalesReport", back_populates="daily_sales")


class OutletMonthlySales(Base):
    """Monthly outlet performance - food cost, gross profit, targets."""
    __tablename__ = "outlet_monthly_sales"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("sales_reports.id"), nullable=False)

    # Identity
    month = Column(String(20), nullable=False)  # e.g., "Apr-26"
    year = Column(Integer, nullable=False)
    outlet = Column(String(100), nullable=False, index=True)

    # Sales
    total_sales = Column(Float, default=0.0)
    daily_avg_sales = Column(Float, default=0.0)

    # Food cost & profit
    opening_stock = Column(Float, default=0.0)
    purchases = Column(Float, default=0.0)
    closing_stock = Column(Float, default=0.0)
    stock_usage = Column(Float, default=0.0)
    food_cost_pct = Column(Float, default=0.0)
    gross_profit_pct = Column(Float, default=0.0)
    gross_profit_rm = Column(Float, default=0.0)

    # Targets
    breakeven = Column(Float, default=0.0)
    target = Column(Float, default=0.0)
    variance = Column(Float, default=0.0)
    variance_pct = Column(Float, default=0.0)

    # Relationships
    report = relationship("SalesReport", back_populates="outlet_monthly")


class DeliverySales(Base):
    """Delivery platform breakdown per outlet."""
    __tablename__ = "delivery_sales"

    id = Column(Integer, primary_key=True, index=True)
    report_id = Column(Integer, ForeignKey("sales_reports.id"), nullable=False)

    # Identity
    month = Column(String(20), nullable=False)
    year = Column(Integer, nullable=False)
    outlet = Column(String(100), nullable=False, index=True)

    # Platform breakdown
    platform = Column(String(50), nullable=False)  # GrabFood, Oddle, Shopee, Beep, InHouse
    revenue = Column(Float, default=0.0)
    trip_count = Column(Integer, default=0)

    # Relationships
    report = relationship("SalesReport", back_populates="delivery_sales")
