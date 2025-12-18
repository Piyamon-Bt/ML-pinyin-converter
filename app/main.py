# # main.py
# from fastapi import FastAPI
# from pydantic import BaseModel, Field
# from app.domain.convert import convert_pinyin_both

# app = FastAPI(title="Chinese → Pinyin API", version="1.1.0")

# class ConvertBothRequest(BaseModel):
#     word: str = Field(..., min_length=1, description="Chinese text")
#     use_sandhi: bool = Field(True, description="ปรับโทนตามกฎ sandhi เบื้องต้นหรือไม่") #ผลคือ ถ้าไม่ส่ง use_sandhi มาก็ถือว่าเปิด; ถ้าจะ “ปิด” ให้ส่ง use_sandhi: false ได้
#     group_by_word: bool = Field(False, description="ให้จัดกลุ่มผลตาม 'คำ' ด้วยหรือไม่")

# @app.post("/pinyin")
# @app.post("/pinyin/")
# def pinyin_both(req: ConvertBothRequest):
#     return convert_pinyin_both(
#     text=req.word,
#     use_sandhi=req.use_sandhi
# )

# @app.get("/")
# def root():
#     return {"ok": True, "usage": "POST /pinyin {word, use_sandhi, group_by_word}"}


# if __name__ == "__main__":
#     import uvicorn
#     uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)


from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.api.v1.router import api_router

app = FastAPI(title="Chinese → Pinyin API", version="1.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Vite dev
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(api_router, prefix="/api/v1") #ทุก route ที่อยู่ใน api_router จะถูกเติม prefix เป็น /api/v1

@app.get("/")
def root():
    return {"ok": True, "usage": "POST /api/v1/pinyin {word, use_sandhi, group_by_word}"}
