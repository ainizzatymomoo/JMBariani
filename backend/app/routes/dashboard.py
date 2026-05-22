"""Dashboard API - Aggregated business intelligence for JM Baryani HQ."""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func as sql_func, desc
from datetime import datetime, timedelta

from app.database import get_db
from app.models.invoice import Invoice, InvoiceItem, Supplier
from app.models.inventory import StockItem, StockMovement, ReorderAlert
from app.models.sales import SalesReport, DailySales, OutletMonthlySales, DeliverySales

router = APIRouter()


@router.get("/overview")
async def get_dashboard_overview(db: Session = Depends(get_db)):
    """
    Master dashboard endpoint - returns all KPIs and data needed
    for the executive overview in one call.
    """

    # --- Invoice Module Stats ---
    total_invoices = db.query(Invoice).count()
    pending_invoices = db.query(Invoice).filter(Invoice.status.in_(["parsed", "manual_required"])).count()
    verified_invoices = db.query(Invoice).filter(Invoice.status == "verified").count()
    total_invoice_value = db.query(sql_func.sum(Invoice.total)).filter(Invoice.status == "verified").scalar() or 0

    # Recent invoices (last 5)
    recent_invoices = db.query(Invoice).order_by(desc(Invoice.created_at)).limit(5).all()
    recent_invoices_data = [{
        "id": inv.id,
        "supplier": inv.supplier.name if inv.supplier else inv.original_filename,
        "total": inv.total,
        "status": inv.status,
        "category": inv.category,
        "date": inv.created_at.isoformat() if inv.created_at else None
    } for inv in recent_invoices]

    # Monthly purchase trend (from invoices)
    monthly_purchases = db.query(
        sql_func.date_trunc('month', Invoice.created_at).label('month'),
        sql_func.sum(Invoice.total).label('total'),
        sql_func.count(Invoice.id).label('count')
    ).filter(Invoice.status == "verified").group_by('month').order_by('month').all()

    purchases_trend = [{
        "month": row.month.strftime("%b %Y") if row.month else "Unknown",
        "total": round(row.total or 0, 2),
        "count": row.count
    } for row in monthly_purchases]

    # --- Inventory Module Stats ---
    total_stock_items = db.query(StockItem).filter(StockItem.is_active == True).count()
    low_stock_items = db.query(StockItem).filter(
        StockItem.is_active == True,
        StockItem.current_stock <= StockItem.minimum_stock,
        StockItem.minimum_stock > 0
    ).count()
    total_inventory_value = db.query(
        sql_func.sum(StockItem.current_stock * StockItem.average_unit_cost)
    ).filter(StockItem.is_active == True).scalar() or 0
    active_alerts = db.query(ReorderAlert).filter(ReorderAlert.status == "active").count()

    # Stock by category
    stock_by_category = db.query(
        StockItem.category,
        sql_func.count(StockItem.id).label('count'),
        sql_func.sum(StockItem.current_stock * StockItem.average_unit_cost).label('value')
    ).filter(StockItem.is_active == True).group_by(StockItem.category).all()

    stock_categories = [{
        "category": row.category,
        "count": row.count,
        "value": round(row.value or 0, 2)
    } for row in stock_by_category]

    # --- Sales Module Stats ---
    total_reports = db.query(SalesReport).filter(SalesReport.status == "parsed").count()

    # Get latest outlet monthly data
    outlet_performance = db.query(OutletMonthlySales).order_by(
        desc(OutletMonthlySales.id)
    ).limit(10).all()

    outlets_data = [{
        "outlet": o.outlet,
        "total_sales": o.total_sales,
        "food_cost_pct": o.food_cost_pct,
        "gross_profit_pct": o.gross_profit_pct,
        "gross_profit_rm": o.gross_profit_rm,
        "daily_avg_sales": o.daily_avg_sales
    } for o in outlet_performance]

    # Daily sales trend
    daily_sales = db.query(DailySales).order_by(DailySales.date).limit(30).all()
    daily_trend = [{
        "date": d.date.strftime("%d %b") if d.date else "Unknown",
        "total": d.total_sales,
        "transactions": d.transaction_count
    } for d in daily_sales]

    # Delivery platform breakdown
    delivery_data = db.query(
        DeliverySales.platform,
        sql_func.sum(DeliverySales.revenue).label('total_revenue'),
        sql_func.sum(DeliverySales.trip_count).label('total_trips')
    ).group_by(DeliverySales.platform).all()

    delivery_platforms = [{
        "platform": d.platform,
        "revenue": round(d.total_revenue or 0, 2),
        "trips": d.total_trips or 0
    } for d in delivery_data]

    # --- Generate Top Insights ---
    insights = _generate_dashboard_insights(
        db, total_invoice_value, low_stock_items, active_alerts,
        outlets_data, delivery_platforms
    )

    # --- Supplier spending (top 5) ---
    top_suppliers = db.query(
        Supplier.name,
        sql_func.sum(Invoice.total).label('total_spend'),
        sql_func.count(Invoice.id).label('invoice_count')
    ).join(Invoice, Invoice.supplier_id == Supplier.id).filter(
        Invoice.status == "verified"
    ).group_by(Supplier.name).order_by(desc('total_spend')).limit(5).all()

    suppliers_data = [{
        "name": s.name,
        "total_spend": round(s.total_spend or 0, 2),
        "invoice_count": s.invoice_count
    } for s in top_suppliers]

    return {
        # KPI Cards
        "kpis": {
            "total_revenue": round(sum(o.get("total_sales", 0) for o in outlets_data), 2),
            "total_expenses": round(total_invoice_value, 2),
            "inventory_value": round(total_inventory_value, 2),
            "active_alerts": active_alerts + pending_invoices,
        },
        # Module summaries
        "invoices": {
            "total": total_invoices,
            "pending": pending_invoices,
            "verified": verified_invoices,
            "total_value": round(total_invoice_value, 2),
            "recent": recent_invoices_data,
            "purchases_trend": purchases_trend
        },
        "inventory": {
            "total_items": total_stock_items,
            "low_stock": low_stock_items,
            "total_value": round(total_inventory_value, 2),
            "alerts": active_alerts,
            "by_category": stock_categories
        },
        "sales": {
            "total_reports": total_reports,
            "outlets": outlets_data,
            "daily_trend": daily_trend,
            "delivery_platforms": delivery_platforms
        },
        # Insights & actions
        "insights": insights,
        "top_suppliers": suppliers_data,
    }


def _generate_dashboard_insights(db, total_expenses, low_stock, alerts, outlets, delivery):
    """Generate priority-sorted business insights for the dashboard."""
    insights = []

    # High food cost
    high_fc_outlets = [o for o in outlets if o.get("food_cost_pct", 0) > 50]
    if high_fc_outlets:
        names = ", ".join(set(o["outlet"] for o in high_fc_outlets))
        insights.append({
            "type": "danger",
            "title": "High Food Cost",
            "message": f"{names} — food cost exceeds 50%. Margin terjejas.",
            "priority": 1
        })

    # Low stock alerts
    if low_stock > 0:
        insights.append({
            "type": "warning",
            "title": f"{low_stock} Items Low Stock",
            "message": "Items dah sampai minimum level. Order sebelum habis.",
            "priority": 2
        })

    # Best performing outlet
    if outlets:
        best = max(outlets, key=lambda x: x.get("gross_profit_pct", 0))
        if best.get("gross_profit_pct", 0) > 0:
            insights.append({
                "type": "positive",
                "title": "Top Performer",
                "message": f"{best['outlet']} — GP {best['gross_profit_pct']:.1f}%, daily avg RM{best.get('daily_avg_sales', 0):,.0f}",
                "priority": 3
            })

    # Delivery platform insight
    if delivery:
        top_platform = max(delivery, key=lambda x: x.get("revenue", 0))
        total_delivery = sum(d.get("revenue", 0) for d in delivery)
        if total_delivery > 0:
            pct = (top_platform["revenue"] / total_delivery) * 100
            insights.append({
                "type": "info",
                "title": "Delivery Dominance",
                "message": f"{top_platform['platform']} = {pct:.0f}% of delivery revenue (RM{top_platform['revenue']:,.0f})",
                "priority": 4
            })

    # Sort by priority
    insights.sort(key=lambda x: x.get("priority", 99))
    return insights
