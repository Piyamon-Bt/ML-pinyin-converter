from fastapi import APIRouter
from app.api.v1.routes.pinyin import router as pinyin_router

api_router = APIRouter()
api_router.include_router(pinyin_router)
