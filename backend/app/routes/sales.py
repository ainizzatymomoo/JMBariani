"""Sales API Routes for JM Baryani HQ."""

import os
import shutil
from typing import List, Optional
from fastapi import APIRouter, Depends, UploadFile, File, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.config import settings
from app.models.sales import SalesReport, DailySales, OutletMonthlySales, DeliverySales
from app.services.sales_parser import sales_parser

router = APIRouter()


@router.post("/upload")
async def upload_report(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    """
    Upload a sales report PDF for parsing.
    Auto-detects report type and extracts structured data + insights.
    """
    filename = file.filename or "unknown"
    ext = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""

    if ext != "pdf":
        raise HTTPException(status_code=400, detail="Only PDF files supported for sales reports")

    # Save file
    upload_dir = os.path.join(settings.UPLOAD_DIR, "reports")
    os.makedirs(upload_dir, exist_ok=True)

    import uuid
    file_id = str(uuid.uuid4())
    saved_filename = f"{file_id}.pdf"
    file_path = os.path.join(upload_dir, saved_filename)

    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Parse the report
    try:
        result = sales_parser.parse_pdf(file_path)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to parse report: {str(e)}")

    # Create report record
    report = SalesReport(
        original_filename=filename,
        file_path=saved_filename,
        report_type=result["report_type"],
        status="parsed"
    )
    db.add(report)
    db.flush()

    # Store parsed data based on report type
    data = result.get("data", {})

    if result["report_type"] == "fc_gp":
        for outlet_data in data.get("outlets", []):
            if outlet_data.get("outlet") == "TOTAL":
                continue
            record = OutletMonthlySales(
                report_id=report.id,
                month=data.get("report_month", ""),
                year=2026,
                outlet=outlet_data["outlet"],
                total_sales=outlet_data.get("total_sales", 0),
                daily_avg_sales=outlet_data.get("daily_avg_sales", 0),
                opening_stock=outlet_data.get("opening_stock", 0),
                purchases=outlet_data.get("purchases", 0),
                closing_stock=outlet_data.get("closing_stock", 0),
                stock_usage=outlet_data.get("stock_usage", 0),
                food_cost_pct=outlet_data.get("food_cost_pct", 0),
                gross_profit_pct=outlet_data.get("gross_profit_pct", 0),
                gross_profit_rm=outlet_data.get("gross_profit_rm", 0),
            )
            db.add(record)

    elif result["report_type"] == "daily_sales":
        for daily in data.get("daily_records", []):
            record = DailySales(
                report_id=report.id,
                date=_parse_date_str(daily.get("date", "")),
                outlet="All Outlets",
                total_sales=daily.get("total_sales", 0),
                transaction_count=daily.get("transaction_count", 0),
                dine_in=0, takeaway=0, delivery=0, catering=0,
            )
            db.add(record)

    elif result["report_type"] in ("delivery_partner", "delivery_detail"):
        outlet_platforms = data.get("outlet_platforms", [])
        for op in outlet_platforms:
            for platform in ["grabfood", "oddle", "beep", "shopee", "inhouse"]:
                revenue = op.get(platform, 0)
                if revenue > 0:
                    record = DeliverySales(
                        report_id=report.id,
                        month="Apr",
                        year=2026,
                        outlet=op.get("outlet", "Unknown"),
                        platform=platform.title(),
                        revenue=revenue,
                    )
                    db.add(record)

    db.commit()
    db.refresh(report)

    return {
        "report_id": report.id,
        "report_type": result["report_type"],
        "filename": filename,
        "status": "parsed",
        "data_summary": _summarize_data(result),
        "insights": result.get("insights", []),
        "message": f"Report parsed successfully. Type: {result['report_type']}"
    }


@router.get("/reports")
async def list_reports(
    report_type: Optional[str] = Query(None),
    db: Session = Depends(get_db)
):
    """List all uploaded sales reports."""
    query = db.query(SalesReport)
    if report_type:
        query = query.filter(SalesReport.report_type == report_type)
    reports = query.order_by(SalesReport.created_at.desc()).all()

    return [{
        "id": r.id,
        "filename": r.original_filename,
        "report_type": r.report_type,
        "status": r.status,
        "created_at": r.created_at.isoformat() if r.created_at else None
    } for r in reports]


@router.get("/reports/{report_id}")
async def get_report(report_id: int, db: Session = Depends(get_db)):
    """Get a parsed report with its data and re-generate insights."""
    report = db.query(SalesReport).filter(SalesReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    # Re-parse the file for full data + insights
    file_path = os.path.join(settings.UPLOAD_DIR, "reports", report.file_path)
    if os.path.exists(file_path):
        result = sales_parser.parse_pdf(file_path)
        return {
            "id": report.id,
            "filename": report.original_filename,
            "report_type": report.report_type,
            "data": result.get("data", {}),
            "insights": result.get("insights", []),
        }

    return {
        "id": report.id,
        "filename": report.original_filename,
        "report_type": report.report_type,
        "data": {},
        "insights": [],
    }


@router.delete("/reports/{report_id}")
async def delete_report(report_id: int, db: Session = Depends(get_db)):
    """Delete a sales report."""
    report = db.query(SalesReport).filter(SalesReport.id == report_id).first()
    if not report:
        raise HTTPException(status_code=404, detail="Report not found")

    if report.file_path:
        file_full = os.path.join(settings.UPLOAD_DIR, "reports", report.file_path)
        if os.path.exists(file_full):
            os.remove(file_full)

    db.delete(report)
    db.commit()
    return {"message": "Report deleted", "id": report_id}


@router.get("/insights")
async def get_all_insights(db: Session = Depends(get_db)):
    """
    Get combined insights from all parsed reports.
    Returns a dashboard-friendly overview.
    """
    reports = db.query(SalesReport).filter(SalesReport.status == "parsed").all()

    all_insights = []
    summary = {
        "total_reports": len(reports),
        "report_types": {},
    }

    for report in reports:
        rt = report.report_type
        summary["report_types"][rt] = summary["report_types"].get(rt, 0) + 1

        # Re-parse for insights
        file_path = os.path.join(settings.UPLOAD_DIR, "reports", report.file_path)
        if os.path.exists(file_path):
            try:
                result = sales_parser.parse_pdf(file_path)
                for insight in result.get("insights", []):
                    insight["source"] = report.original_filename
                    all_insights.append(insight)
            except Exception:
                continue

    return {
        "summary": summary,
        "insights": all_insights
    }


@router.post("/parse-test")
async def parse_test_reports(db: Session = Depends(get_db)):
    """
    Parse all PDF files in the test_report/ folder.
    Useful for testing/demo without manual upload.
    """
    test_dir = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__)))), "test_report")

    if not os.path.exists(test_dir):
        # Try Docker mount path
        test_dir = "/app/test_report"

    if not os.path.exists(test_dir):
        raise HTTPException(status_code=404, detail="test_report folder not found")

    files = sorted([f for f in os.listdir(test_dir) if f.lower().endswith('.pdf')])
    if not files:
        raise HTTPException(status_code=404, detail="No PDF files in test_report/")

    results = []
    for filename in files:
        filepath = os.path.join(test_dir, filename)
        try:
            result = sales_parser.parse_pdf(filepath)

            # Save report record
            report = SalesReport(
                original_filename=filename,
                file_path=f"test_{filename}",
                report_type=result["report_type"],
                status="parsed"
            )
            db.add(report)
            db.flush()

            results.append({
                "filename": filename,
                "report_type": result["report_type"],
                "insights_count": len(result.get("insights", [])),
                "insights": result.get("insights", []),
                "data_summary": _summarize_data(result)
            })
        except Exception as e:
            results.append({
                "filename": filename,
                "error": str(e)
            })

    db.commit()

    return {
        "message": f"Parsed {len(results)} test reports",
        "results": results
    }


# --- Helper Functions ---

def _parse_date_str(date_str: str):
    """Parse date string like '1-Apr-26' to date object."""
    from datetime import datetime
    try:
        return datetime.strptime(date_str, "%d-%b-%y").date()
    except (ValueError, TypeError):
        return None


def _summarize_data(result: Dict) -> Dict:
    """Create a brief summary of parsed data."""
    data = result.get("data", {})
    report_type = result.get("report_type", "")
    summary = {"report_type": report_type}

    if report_type == "fc_gp":
        outlets = data.get("outlets", [])
        total = next((o for o in outlets if o.get("outlet") == "TOTAL"), None)
        if total:
            summary["total_sales"] = total.get("total_sales", 0)
            summary["food_cost_pct"] = total.get("food_cost_pct", 0)
            summary["gross_profit_pct"] = total.get("gross_profit_pct", 0)
        summary["outlets_count"] = len([o for o in outlets if o.get("outlet") != "TOTAL"])

    elif report_type == "daily_sales":
        summary["total_sales"] = data.get("total_sales", 0)
        summary["days_count"] = data.get("days_count", 0)
        summary["channels"] = data.get("channel_percentages", {})

    elif report_type == "ytd_sales":
        summary["grand_total"] = data.get("grand_total", 0)
        summary["outlets_count"] = len(data.get("outlets_monthly", []))

    elif report_type in ("delivery_partner", "delivery_detail"):
        summary["total_sales"] = data.get("total_sales", 0)
        summary["platforms_count"] = len(data.get("platform_totals", []))

    return summary


# Need this import for type hint
from typing import Dict
