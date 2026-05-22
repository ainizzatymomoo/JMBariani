"""Invoice API Routes for JM Baryani HQ."""

import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.invoice import Invoice, InvoiceItem, Supplier
from app.schemas.invoice import (
    InvoiceResponse, InvoiceUpdate, OCRResultResponse,
    InvoiceItemCreate, SupplierResponse, SupplierCreate
)
from app.services.ocr_service import ocr_service
from app.services.invoice_parser import invoice_parser

router = APIRouter()


@router.post("/upload", response_model=OCRResultResponse)
async def upload_invoice(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload an invoice file (PDF/image) for OCR processing.
    Returns parsed invoice data for review.
    """
    # Validate file type
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    allowed_types = {"pdf", "jpg", "jpeg", "png", "tiff", "bmp"}

    if ext not in allowed_types:
        raise HTTPException(
            status_code=400,
            detail=f"File type '{ext}' not supported. Use: {allowed_types}"
        )

    # Save file
    upload_dir = settings.UPLOAD_DIR
    os.makedirs(upload_dir, exist_ok=True)

    import uuid
    file_id = str(uuid.uuid4())
    saved_filename = f"{file_id}.{ext}"
    file_path = os.path.join(upload_dir, saved_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Run OCR
    try:
        raw_text, confidence = ocr_service.extract_text(file_path, ext)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"OCR failed: {str(e)}")

    # Determine if manual input is needed (confidence < 60%)
    LOW_CONFIDENCE_THRESHOLD = 60.0
    needs_manual_input = confidence < LOW_CONFIDENCE_THRESHOLD

    # Parse extracted text (even for low confidence, try to get what we can)
    parsed_data = invoice_parser.parse(raw_text)

    # Find or create supplier
    supplier_id = None
    if parsed_data.get("supplier_name"):
        supplier = db.query(Supplier).filter(
            Supplier.name.ilike(f"%{parsed_data['supplier_name']}%")
        ).first()
        if not supplier:
            supplier = Supplier(name=parsed_data["supplier_name"])
            db.add(supplier)
            db.flush()
        supplier_id = supplier.id

    # Set status based on confidence
    status = "manual_required" if needs_manual_input else "parsed"

    # Create invoice record
    invoice = Invoice(
        supplier_id=supplier_id,
        invoice_number=parsed_data.get("invoice_number"),
        invoice_date=parsed_data.get("invoice_date"),
        subtotal=parsed_data.get("subtotal", 0),
        tax=parsed_data.get("tax", 0),
        total=parsed_data.get("total", 0),
        status=status,
        ocr_raw_text=raw_text,
        ocr_confidence=confidence,
        original_filename=filename,
        file_path=saved_filename,
        file_type=ext,
        category=parsed_data.get("category", "lain")
    )
    db.add(invoice)
    db.flush()

    # Create invoice items (only if confidence is acceptable)
    if not needs_manual_input:
        for item_data in parsed_data.get("items", []):
            item = InvoiceItem(
                invoice_id=invoice.id,
                name=item_data["name"],
                quantity=item_data.get("quantity", 1),
                unit=item_data.get("unit"),
                unit_price=item_data.get("unit_price", 0),
                total_price=item_data.get("total_price", 0),
                category=item_data.get("category", "lain")
            )
            db.add(item)

    db.commit()
    db.refresh(invoice)

    if needs_manual_input:
        message = (
            f"OCR confidence too low ({confidence:.1f}%). "
            f"Please enter invoice details manually."
        )
    else:
        message = f"Invoice processed. Confidence: {confidence:.1f}%. Please review."

    return OCRResultResponse(
        invoice_id=invoice.id,
        status=status,
        ocr_confidence=confidence,
        parsed_data=parsed_data,
        message=message
    )


@router.get("/", response_model=List[InvoiceResponse])
async def list_invoices(
    status: Optional[str] = Query(None),
    category: Optional[str] = Query(None),
    skip: int = Query(0, ge=0),
    limit: int = Query(50, ge=1, le=200),
    db: Session = Depends(get_db)
):
    """List all invoices with optional filters."""
    query = db.query(Invoice)

    if status:
        query = query.filter(Invoice.status == status)
    if category:
        query = query.filter(Invoice.category == category)

    query = query.order_by(Invoice.created_at.desc())
    invoices = query.offset(skip).limit(limit).all()
    return invoices


@router.get("/{invoice_id}", response_model=InvoiceResponse)
async def get_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Get a single invoice by ID."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")
    return invoice


@router.put("/{invoice_id}", response_model=InvoiceResponse)
async def update_invoice(
    invoice_id: int,
    update: InvoiceUpdate,
    db: Session = Depends(get_db)
):
    """Update/correct invoice data (manual correction after OCR)."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Update basic fields
    update_data = update.model_dump(exclude_unset=True, exclude={"items"})

    # Handle supplier name update
    if "supplier_name" in update_data:
        supplier_name = update_data.pop("supplier_name")
        if supplier_name:
            supplier = db.query(Supplier).filter(
                Supplier.name.ilike(f"%{supplier_name}%")
            ).first()
            if not supplier:
                supplier = Supplier(name=supplier_name)
                db.add(supplier)
                db.flush()
            invoice.supplier_id = supplier.id

    for field, value in update_data.items():
        if hasattr(invoice, field):
            setattr(invoice, field, value)

    # Update items if provided
    if update.items is not None:
        # Delete existing items
        db.query(InvoiceItem).filter(
            InvoiceItem.invoice_id == invoice_id
        ).delete()

        # Add new items
        for item_data in update.items:
            item = InvoiceItem(
                invoice_id=invoice_id,
                name=item_data.name,
                quantity=item_data.quantity,
                unit=item_data.unit,
                unit_price=item_data.unit_price,
                total_price=item_data.total_price,
                category=item_data.category
            )
            db.add(item)

    # Mark as verified if corrected
    if not update.status:
        invoice.status = "verified"

    db.commit()
    db.refresh(invoice)
    return invoice


@router.delete("/{invoice_id}")
async def delete_invoice(invoice_id: int, db: Session = Depends(get_db)):
    """Delete an invoice."""
    invoice = db.query(Invoice).filter(Invoice.id == invoice_id).first()
    if not invoice:
        raise HTTPException(status_code=404, detail="Invoice not found")

    # Delete file
    if invoice.file_path:
        file_full_path = os.path.join(settings.UPLOAD_DIR, invoice.file_path)
        if os.path.exists(file_full_path):
            os.remove(file_full_path)

    db.delete(invoice)
    db.commit()
    return {"message": "Invoice deleted", "id": invoice_id}


@router.get("/suppliers/", response_model=List[SupplierResponse])
async def list_suppliers(db: Session = Depends(get_db)):
    """List all suppliers."""
    return db.query(Supplier).order_by(Supplier.name).all()


@router.post("/suppliers/", response_model=SupplierResponse)
async def create_supplier(
    supplier: SupplierCreate,
    db: Session = Depends(get_db)
):
    """Create a new supplier."""
    db_supplier = Supplier(**supplier.model_dump())
    db.add(db_supplier)
    db.commit()
    db.refresh(db_supplier)
    return db_supplier
