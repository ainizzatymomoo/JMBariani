from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
import os

from app.config import settings
from app.database import init_db
from app.routes import invoices, health, inventory, sales, dashboard, auth
from app.routes.auth import get_current_user

app = FastAPI(
    title=settings.APP_NAME,
    description="Business Intelligence System for JM Baryani",
    version="0.1.0"
)

# CORS - allow frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000", "http://127.0.0.1:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Ensure upload directory exists
os.makedirs(settings.UPLOAD_DIR, exist_ok=True)

# Mount uploads as static files
app.mount("/uploads", StaticFiles(directory=settings.UPLOAD_DIR), name="uploads")

# --- Public routes (no auth required) ---
app.include_router(health.router, tags=["Health"])
app.include_router(auth.router, prefix="/api/auth", tags=["Auth"])

# --- Protected routes (require login) ---
app.include_router(
    invoices.router, prefix="/api/invoices", tags=["Invoices"],
    dependencies=[Depends(get_current_user)]
)
app.include_router(
    inventory.router, prefix="/api/inventory", tags=["Inventory"],
    dependencies=[Depends(get_current_user)]
)
app.include_router(
    sales.router, prefix="/api/sales", tags=["Sales"],
    dependencies=[Depends(get_current_user)]
)
app.include_router(
    dashboard.router, prefix="/api/dashboard", tags=["Dashboard"],
    dependencies=[Depends(get_current_user)]
)


@app.on_event("startup")
async def startup():
    """Initialize database on startup."""
    init_db()
    print(f"🍚 {settings.APP_NAME} Backend Started!")
    print(f"📄 Invoice OCR Module Ready")
    print(f"📦 Inventory Management Ready")
    print(f"🔐 Auth: Protected routes require login")
