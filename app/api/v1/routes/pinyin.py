from fastapi import APIRouter
from app.schemas.pinyin import ConvertBothRequest, ConvertBothResponse
from app.services.pinyin_service import pinyin_both_service
from app.repositories.history_repo import get_all, clear

router = APIRouter(prefix="/pinyin", tags=["pinyin"]) # หรือ include พร้อม prefix เพิ่มก็ได้

@router.post("", response_model=ConvertBothResponse)
def pinyin_both(req: ConvertBothRequest):
    result = pinyin_both_service(req.word, req.use_sandhi)
    return ConvertBothResponse(result=result)

#Path parameter ก็ match ได้
# @router.get("/{id}")
# def get_one(id: int): ...

@router.get("/history")
def history():
    return {"items": get_all()} #"items" = “กล่อง/หัวข้อ” ที่ห่อ list ของประวัติไว้

@router.delete("/history")
def clear_history():
    clear()
    return {"ok": True}