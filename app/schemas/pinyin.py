from pydantic import BaseModel, Field

class ConvertBothRequest(BaseModel):
    word: str = Field(..., min_length=1, description="Chinese text")
    use_sandhi: bool = Field(True, description="ปรับโทนตามกฎ sandhi เบื้องต้นหรือไม่") #ผลคือ ถ้าไม่ส่ง use_sandhi มาก็ถือว่าเปิด; ถ้าจะ “ปิด” ให้ส่ง use_sandhi: false ได้
    # group_by_word: bool = Field(False, description="ให้จัดกลุ่มผลตาม 'คำ' ด้วยหรือไม่")

class ConvertBothResponse(BaseModel):
    result: object  # หรือกำหนดเป็น str/dict ให้ชัดตาม output จริงของคุณ