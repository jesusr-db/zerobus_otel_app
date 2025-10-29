# Generic router module for the Databricks app template
# Add your FastAPI routes here

from fastapi import APIRouter

from .user import router as user_router
from .services import router as services_router
from .dependencies import router as dependencies_router
from .warehouse import router as warehouse_router

router = APIRouter()
router.include_router(user_router, prefix='/user', tags=['user'])
router.include_router(services_router, prefix='/services', tags=['services'])
router.include_router(dependencies_router, prefix='/dependencies', tags=['dependencies'])
router.include_router(warehouse_router, prefix='/warehouse', tags=['warehouse'])
