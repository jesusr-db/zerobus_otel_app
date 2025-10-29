from fastapi import APIRouter, HTTPException, Request
from server.models.observability import WarehouseInfo
from server.services.warehouse_manager import WarehouseManager

router = APIRouter()


@router.get("/info")
async def get_warehouse_info(request: Request) -> WarehouseInfo:
    try:
        user_token = request.headers.get("X-Forwarded-Access-Token")
        warehouse_manager = WarehouseManager(user_token=user_token)
        info = warehouse_manager.get_warehouse_info()
        return WarehouseInfo(**info)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to get warehouse info: {str(e)}")
