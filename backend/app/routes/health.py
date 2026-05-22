from fastapi import APIRouter

router = APIRouter()


@router.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "service": "JM Baryani HQ",
        "module": "Invoice OCR"
    }
