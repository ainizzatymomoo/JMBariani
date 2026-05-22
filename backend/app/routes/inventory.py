"""Inventory API Routes for JM Baryani HQ."""

from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.inventory import StockItem, StockMovement, ReorderAlert
from app.schemas.inventory import (
    StockItemCreate, StockItemUpdate, StockItemResponse, StockItemSummary,
    StockMovementCreate, StockMovementResponse,
    ReorderAlertResponse, InventorySummary
)
from app.services.inventory_engine import inventory_engine

router = APIRouter()


# --- Stock Items ---

@router.get("/items", response_model=List[StockItemResponse])
async def list_stock_items(
    category: Optional[str] = Query(None),
    low_stock_only: bool = Query(False),
    is_active: bool = Query(True),
    skip: int = Query(0, ge=0),
    limit: int = Query(100, ge=1, le=500),
    db: Session = Depends(get_db)
):
    """List all inventory items with optional filters."""
    query = db.query(StockItem).filter(StockItem.is_active == is_active)

    if category:
        query = query.filter(StockItem.category == category)
    if low_stock_only:
        query = query.filter(
            StockItem.current_stock <= StockItem.minimum_stock,
            StockItem.minimum_stock > 0
        )

    query = query.order_by(StockItem.name)
    return query.offset(skip).limit(limit).all()


@router.post("/items", response_model=StockItemResponse)
async def create_stock_item(
    item: StockItemCreate,
    db: Session = Depends(get_db)
):
    """Create a new stock item."""
    db_item = StockItem(**item.model_dump())
    db.add(db_item)
    db.commit()
    db.refresh(db_item)
    return db_item


@router.get("/items/{item_id}", response_model=StockItemResponse)
async def get_stock_item(item_id: int, db: Session = Depends(get_db)):
    """Get a single stock item."""
    item = db.query(StockItem).filter(StockItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Stock item not found")
    return item


@router.put("/items/{item_id}", response_model=StockItemResponse)
async def update_stock_item(
    item_id: int,
    update: StockItemUpdate,
    db: Session = Depends(get_db)
):
    """Update a stock item."""
    item = db.query(StockItem).filter(StockItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    update_data = update.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(item, field, value)

    db.commit()
    db.refresh(item)
    return item


@router.delete("/items/{item_id}")
async def delete_stock_item(item_id: int, db: Session = Depends(get_db)):
    """Soft-delete a stock item (mark inactive)."""
    item = db.query(StockItem).filter(StockItem.id == item_id).first()
    if not item:
        raise HTTPException(status_code=404, detail="Stock item not found")

    item.is_active = False
    db.commit()
    return {"message": "Stock item deactivated", "id": item_id}


# --- Stock Movements ---

@router.post("/movements", response_model=StockMovementResponse)
async def create_movement(
    movement: StockMovementCreate,
    db: Session = Depends(get_db)
):
    """Record a stock movement (in/out/adjustment/waste)."""
    try:
        if movement.movement_type == "in":
            result = inventory_engine.stock_in(
                db=db,
                stock_item_id=movement.stock_item_id,
                quantity=movement.quantity,
                unit_cost=movement.unit_cost or 0,
                reference_type=movement.reference_type,
                reference_id=movement.reference_id,
                notes=movement.notes
            )
        elif movement.movement_type == "out":
            result = inventory_engine.stock_out(
                db=db,
                stock_item_id=movement.stock_item_id,
                quantity=movement.quantity,
                reference_type=movement.reference_type,
                reference_id=movement.reference_id,
                notes=movement.notes
            )
        elif movement.movement_type == "adjustment":
            result = inventory_engine.adjust_stock(
                db=db,
                stock_item_id=movement.stock_item_id,
                new_quantity=movement.quantity,
                notes=movement.notes
            )
        elif movement.movement_type == "waste":
            result = inventory_engine.record_waste(
                db=db,
                stock_item_id=movement.stock_item_id,
                quantity=movement.quantity,
                notes=movement.notes
            )
        else:
            raise HTTPException(
                status_code=400,
                detail="Invalid movement_type. Use: in, out, adjustment, waste"
            )

        db.commit()
        return result

    except ValueError as e:
        raise HTTPException(status_code=404, detail=str(e))


@router.get("/movements", response_model=List[StockMovementResponse])
async def list_movements(
    stock_item_id: Optional[int] = Query(None),
    movement_type: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List stock movements with optional filters."""
    query = db.query(StockMovement)

    if stock_item_id:
        query = query.filter(StockMovement.stock_item_id == stock_item_id)
    if movement_type:
        query = query.filter(StockMovement.movement_type == movement_type)

    query = query.order_by(StockMovement.movement_date.desc())
    return query.offset(skip).limit(limit).all()


# --- Alerts & Summary ---

@router.get("/alerts", response_model=List[ReorderAlertResponse])
async def list_alerts(
    status: str = Query("active"),
    db: Session = Depends(get_db)
):
    """List reorder alerts."""
    query = db.query(ReorderAlert)
    if status:
        query = query.filter(ReorderAlert.status == status)
    return query.order_by(ReorderAlert.created_at.desc()).all()


@router.put("/alerts/{alert_id}/acknowledge")
async def acknowledge_alert(alert_id: int, db: Session = Depends(get_db)):
    """Acknowledge a reorder alert."""
    alert = db.query(ReorderAlert).filter(ReorderAlert.id == alert_id).first()
    if not alert:
        raise HTTPException(status_code=404, detail="Alert not found")

    from datetime import datetime
    alert.status = "acknowledged"
    alert.acknowledged_at = datetime.utcnow()
    db.commit()
    return {"message": "Alert acknowledged", "id": alert_id}


@router.get("/summary", response_model=InventorySummary)
async def get_inventory_summary(db: Session = Depends(get_db)):
    """Get inventory dashboard summary."""
    return inventory_engine.get_summary(db)


@router.get("/reorder-suggestions")
async def get_reorder_suggestions(db: Session = Depends(get_db)):
    """Get smart reorder suggestions based on usage patterns."""
    return inventory_engine.get_reorder_suggestions(db)


@router.post("/process-invoice/{invoice_id}")
async def process_invoice_to_inventory(
    invoice_id: int,
    db: Session = Depends(get_db)
):
    """
    Process a verified invoice into inventory stock-in movements.
    Creates stock items if they don't exist.
    """
    try:
        movements = inventory_engine.process_invoice_to_stock(db, invoice_id)
        db.commit()
        return {
            "message": f"Invoice processed. {len(movements)} items added to inventory.",
            "movements_count": len(movements),
            "invoice_id": invoice_id
        }
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
