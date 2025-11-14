from fastapi import APIRouter
from services.db_service import get_orders

router = APIRouter()

@router.get("/")
def list_orders():
    return get_orders()
