# main.py
from fastapi import FastAPI
from pydantic import BaseModel, Field
from convert import convert_pinyin_both

app = FastAPI(title="Chinese → Pinyin API", version="1.1.0")

class ConvertBothRequest(BaseModel):
    word: str = Field(..., min_length=1, description="Chinese text")
    use_sandhi: bool = Field(False, description="ปรับโทนตามกฎ sandhi เบื้องต้นหรือไม่")
    group_by_word: bool = Field(False, description="ให้จัดกลุ่มผลตาม 'คำ' ด้วยหรือไม่")

@app.post("/pinyin")
@app.post("/pinyin/")
def pinyin_both(req: ConvertBothRequest):
    return convert_pinyin_both(
    text=req.word,
    use_sandhi=req.use_sandhi
)

@app.get("/")
def root():
    return {"ok": True, "usage": "POST /pinyin {word, use_sandhi, group_by_word}"}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
