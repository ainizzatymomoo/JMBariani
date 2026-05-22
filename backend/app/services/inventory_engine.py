"""
Inventory Engine for JM Baryani HQ.
Handles stock calculations, movements, reorder alerts, and usage patterns.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func

from app.models.inventory import StockItem, StockMovement, ReorderAlert
from app.models.invoice import Invoice, InvoiceItem


class InventoryEngine:
    """Core business logic for inventory management."""

    # Default lead time for suppliers (days)
    DEFAULT_LEAD_TIME = 2

    # Rolling average window (days)
    USAGE_WINDOW_DAYS = 7

    def stock_in(
        self,
        db: Session,
        stock_item_id: int,
        quantity: float,
        unit_cost: float = 0.0,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> StockMovement:
        """
        Add stock to an item (e.g., from verified invoice).
        Updates current stock and weighted average cost.
        """
        item = db.query(StockItem).filter(StockItem.id == stock_item_id).first()
        if not item:
            raise ValueError(f"Stock item {stock_item_id} not found")

        # Calculate new weighted average cost
        if item.current_stock > 0 and unit_cost > 0:
            total_value = (item.current_stock * item.average_unit_cost) + (quantity * unit_cost)
            new_total = item.current_stock + quantity
            item.average_unit_cost = total_value / new_total if new_total > 0 else 0
        elif unit_cost > 0:
            item.average_unit_cost = unit_cost

        # Update stock
        item.current_stock += quantity
        item.last_unit_cost = unit_cost if unit_cost > 0 else item.last_unit_cost

        # Record movement
        movement = StockMovement(
            stock_item_id=stock_item_id,
            movement_type="in",
            quantity=quantity,
            unit_cost=unit_cost,
            total_cost=quantity * unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            stock_after=item.current_stock
        )
        db.add(movement)

        # Update days of stock
        self._update_days_of_stock(item)

        # Check and resolve any active alerts
        self._check_resolve_alerts(db, item)

        db.flush()
        return movement

    def stock_out(
        self,
        db: Session,
        stock_item_id: int,
        quantity: float,
        reference_type: Optional[str] = None,
        reference_id: Optional[int] = None,
        notes: Optional[str] = None
    ) -> StockMovement:
        """
        Remove stock from an item (e.g., from sales/usage).
        """
        item = db.query(StockItem).filter(StockItem.id == stock_item_id).first()
        if not item:
            raise ValueError(f"Stock item {stock_item_id} not found")

        # Allow negative stock with warning
        item.current_stock -= quantity

        # Record movement
        movement = StockMovement(
            stock_item_id=stock_item_id,
            movement_type="out",
            quantity=-quantity,  # Negative for out
            unit_cost=item.average_unit_cost,
            total_cost=quantity * item.average_unit_cost,
            reference_type=reference_type,
            reference_id=reference_id,
            notes=notes,
            stock_after=item.current_stock
        )
        db.add(movement)

        # Update days of stock
        self._update_days_of_stock(item)

        # Check for low stock alert
        self._check_create_alert(db, item)

        db.flush()
        return movement

    def adjust_stock(
        self,
        db: Session,
        stock_item_id: int,
        new_quantity: float,
        notes: Optional[str] = "Manual adjustment"
    ) -> StockMovement:
        """
        Set stock to a specific level (manual count/adjustment).
        """
        item = db.query(StockItem).filter(StockItem.id == stock_item_id).first()
        if not item:
            raise ValueError(f"Stock item {stock_item_id} not found")

        difference = new_quantity - item.current_stock
        item.current_stock = new_quantity

        movement = StockMovement(
            stock_item_id=stock_item_id,
            movement_type="adjustment",
            quantity=difference,
            unit_cost=item.average_unit_cost,
            total_cost=abs(difference) * item.average_unit_cost,
            reference_type="manual",
            notes=notes,
            stock_after=item.current_stock
        )
        db.add(movement)

        self._update_days_of_stock(item)
        db.flush()
        return movement

    def record_waste(
        self,
        db: Session,
        stock_item_id: int,
        quantity: float,
        notes: Optional[str] = None
    ) -> StockMovement:
        """Record stock waste/spoilage."""
        item = db.query(StockItem).filter(StockItem.id == stock_item_id).first()
        if not item:
            raise ValueError(f"Stock item {stock_item_id} not found")

        item.current_stock -= quantity

        movement = StockMovement(
            stock_item_id=stock_item_id,
            movement_type="waste",
            quantity=-quantity,
            unit_cost=item.average_unit_cost,
            total_cost=quantity * item.average_unit_cost,
            reference_type="waste",
            notes=notes or "Spoilage/waste",
            stock_after=item.current_stock
        )
        db.add(movement)

        self._update_days_of_stock(item)
        self._check_create_alert(db, item)
        db.flush()
        return movement

    def process_invoice_to_stock(self, db: Session, invoice_id: int) -> List[StockMovement]:
        """
        Process a verified invoice and add items to inventory.
        Creates stock items if they don't exist, then records stock-in movements.
        """
        invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
        if not invoice:
            raise ValueError(f"Invoice {invoice_id} not found")

        if invoice.status != "verified":
            raise ValueError(f"Invoice must be verified first (current: {invoice.status})")

        movements = []
        for inv_item in invoice.items:
            # Find or create stock item
            stock_item = self._find_or_create_stock_item(db, inv_item, invoice.supplier_id)

            # Record stock in
            movement = self.stock_in(
                db=db,
                stock_item_id=stock_item.id,
                quantity=inv_item.quantity,
                unit_cost=inv_item.unit_price,
                reference_type="invoice",
                reference_id=invoice.id,
                notes=f"From invoice: {invoice.original_filename or invoice.invoice_number}"
            )
            movements.append(movement)

        return movements

    def get_summary(self, db: Session) -> Dict[str, Any]:
        """Get inventory dashboard summary."""
        items = db.query(StockItem).filter(StockItem.is_active == True).all()

        total_value = sum(i.current_stock * i.average_unit_cost for i in items)
        low_stock = [i for i in items if i.current_stock <= i.minimum_stock and i.minimum_stock > 0]
        basah = [i for i in items if i.category == "basah"]
        kering = [i for i in items if i.category == "kering"]

        active_alerts = db.query(ReorderAlert).filter(
            ReorderAlert.status == "active"
        ).count()

        return {
            "total_items": len(items),
            "total_value": round(total_value, 2),
            "low_stock_count": len(low_stock),
            "basah_items": len(basah),
            "kering_items": len(kering),
            "active_alerts": active_alerts
        }

    def get_reorder_suggestions(self, db: Session) -> List[Dict[str, Any]]:
        """
        Get smart reorder suggestions based on usage patterns.
        Suggests order quantity = (avg_daily_usage * lead_time * 1.5) - current_stock
        """
        items = db.query(StockItem).filter(
            StockItem.is_active == True,
            StockItem.current_stock <= StockItem.minimum_stock
        ).all()

        suggestions = []
        for item in items:
            if item.avg_daily_usage > 0:
                # Order enough for lead_time + safety buffer
                target_stock = item.avg_daily_usage * self.DEFAULT_LEAD_TIME * 1.5
                suggested_qty = max(0, target_stock - item.current_stock)
            else:
                suggested_qty = item.minimum_stock - item.current_stock

            if suggested_qty > 0:
                suggestions.append({
                    "stock_item_id": item.id,
                    "item_name": item.name,
                    "category": item.category,
                    "current_stock": item.current_stock,
                    "minimum_stock": item.minimum_stock,
                    "suggested_qty": round(suggested_qty, 2),
                    "unit": item.unit,
                    "estimated_cost": round(suggested_qty * item.last_unit_cost, 2),
                    "days_until_stockout": item.days_of_stock
                })

        return sorted(suggestions, key=lambda x: x["days_until_stockout"])

    def calculate_usage(self, db: Session, stock_item_id: int) -> float:
        """Calculate average daily usage over the rolling window."""
        window_start = datetime.utcnow() - timedelta(days=self.USAGE_WINDOW_DAYS)

        # Sum of all outgoing movements in the window
        total_out = db.query(sql_func.sum(sql_func.abs(StockMovement.quantity))).filter(
            StockMovement.stock_item_id == stock_item_id,
            StockMovement.movement_type.in_(["out", "waste"]),
            StockMovement.movement_date >= window_start
        ).scalar() or 0.0

        avg_daily = total_out / self.USAGE_WINDOW_DAYS
        return round(avg_daily, 3)

    def update_all_usage_stats(self, db: Session):
        """Recalculate usage stats for all active items."""
        items = db.query(StockItem).filter(StockItem.is_active == True).all()
        for item in items:
            item.avg_daily_usage = self.calculate_usage(db, item.id)
            self._update_days_of_stock(item)
        db.flush()

    # --- Private Helpers ---

    def _find_or_create_stock_item(
        self, db: Session, inv_item: InvoiceItem, supplier_id: Optional[int]
    ) -> StockItem:
        """Find existing stock item by name or create new one."""
        # Try to find by similar name
        stock_item = db.query(StockItem).filter(
            StockItem.name.ilike(f"%{inv_item.name}%"),
            StockItem.is_active == True
        ).first()

        if not stock_item:
            # Create new stock item
            stock_item = StockItem(
                name=inv_item.name,
                category=inv_item.category or "lain",
                unit=inv_item.unit or "unit",
                current_stock=0.0,
                minimum_stock=0.0,  # User can set later
                supplier_id=supplier_id
            )
            db.add(stock_item)
            db.flush()

        return stock_item

    def _update_days_of_stock(self, item: StockItem):
        """Update the estimated days of stock remaining."""
        if item.avg_daily_usage > 0:
            item.days_of_stock = round(item.current_stock / item.avg_daily_usage, 1)
        else:
            item.days_of_stock = 999.0 if item.current_stock > 0 else 0.0

    def _check_create_alert(self, db: Session, item: StockItem):
        """Check if item needs a reorder alert."""
        if item.minimum_stock <= 0:
            return

        if item.current_stock <= item.minimum_stock:
            # Check if active alert already exists
            existing = db.query(ReorderAlert).filter(
                ReorderAlert.stock_item_id == item.id,
                ReorderAlert.status == "active"
            ).first()

            if not existing:
                suggested_qty = 0.0
                if item.avg_daily_usage > 0:
                    suggested_qty = item.avg_daily_usage * self.DEFAULT_LEAD_TIME * 1.5
                else:
                    suggested_qty = item.minimum_stock * 2

                alert = ReorderAlert(
                    stock_item_id=item.id,
                    current_stock=item.current_stock,
                    minimum_stock=item.minimum_stock,
                    suggested_order_qty=round(suggested_qty, 2),
                    days_until_stockout=item.days_of_stock,
                    status="active"
                )
                db.add(alert)

    def _check_resolve_alerts(self, db: Session, item: StockItem):
        """Resolve alerts if stock is back above minimum."""
        if item.current_stock > item.minimum_stock:
            active_alerts = db.query(ReorderAlert).filter(
                ReorderAlert.stock_item_id == item.id,
                ReorderAlert.status == "active"
            ).all()

            for alert in active_alerts:
                alert.status = "resolved"
                alert.resolved_at = datetime.utcnow()


# Singleton instance
inventory_engine = InventoryEngine()
