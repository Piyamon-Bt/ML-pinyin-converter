from app.domain.convert import convert_pinyin_both
from app.repositories.history_repo import add_record

# def pinyin_both_service(word: str, use_sandhi: bool): #ค่าจาก schema มาจับกับ ค่าที่ function รับ
#     return convert_pinyin_both(
#         text=word,
#         use_sandhi=use_sandhi,
#     )

def pinyin_both_service(word: str, use_sandhi: bool):
    result = convert_pinyin_both(text=word, use_sandhi=use_sandhi)

    add_record({
        # "input": word,
        # "use_sandhi": use_sandhi,
        "result": result,
    })
    return result