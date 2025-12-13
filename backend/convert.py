# convert.py
from typing import List, Tuple, Dict
from g2pM import G2pM
import jieba
import re

# โหลดตัวแปลงครั้งเดียว
_g2p = G2pM()

# ---------- tone number → tone mark ----------
VOWELS = 'aeiouvüAEIOUVÜ'
TONE_MARKS = {
    'a': ['ā','á','ǎ','à'], 'e': ['ē','é','ě','è'], 'i': ['ī','í','ǐ','ì'],
    'o': ['ō','ó','ǒ','ò'], 'u': ['ū','ú','ǔ','ù'], 'v': ['ǖ','ǘ','ǚ','ǜ'], 'ü': ['ǖ','ǘ','ǚ','ǜ'],
    'A': ['Ā','Á','Ǎ','À'], 'E': ['Ē','É','Ě','È'], 'I': ['Ī','Í','Ǐ','Ì'],
    'O': ['Ō','Ó','Ǒ','Ò'], 'U': ['Ū','Ú','Ǔ','Ù'], 'V': ['Ǖ','Ǘ','Ǚ','Ǜ'], 'Ü': ['Ǖ','Ǘ','Ǚ','Ǜ'],
}
PRIORITY = ['a','e','o']  # a > e > o > (i/u/ü)

def _choose_tone_index(base: str) -> int:
    low = base.lower()
    # เคสพิเศษตามมาตรฐานพินอิน
    if 'iu' in low:
        return low.index('iu') + 1   # ทำเครื่องหมายที่ 'u'
    if 'ui' in low:
        return low.index('ui')       # ทำเครื่องหมายที่ 'i'
    # a > e > o
    for p in PRIORITY:
        pos = low.find(p)
        if pos != -1:
            return pos
    # ไม่เจอ a/e/o → ใช้สระตัวแรกที่เหลือ (i/u/ü…)
    for i, ch in enumerate(base):
        if ch in VOWELS:
            return i
    return -1

def number_to_mark(syl: str) -> str:
    """'wo3' -> 'wǒ', 'lv4'/'lü4' -> 'lǜ', โทนกลางคืน base เดิม"""
    if not syl:
        return syl
    tone = syl[-1]
    base = syl[:-1]
    base = (base.replace('u:', 'ü').replace('U:', 'Ü')
                 .replace('v', 'ü').replace('V', 'Ü'))
    if tone not in '1234':  # neutral tone
        return base or syl
    idx = _choose_tone_index(base)
    if idx == -1:
        return syl
    vowel = base[idx]
    table = TONE_MARKS.get(vowel)
    if not table:
        return syl
    marked = table[int(tone)-1]
    return base[:idx] + marked + base[idx+1:]

# --------- (ทางเลือก) tone sandhi แบบง่าย ----------
def apply_basic_sandhi(syllables: List[str]) -> List[str]:
    """
    กฎพื้นฐาน:
    - 不 bù: ปกติ bu4; ถ้าหน้าคำโทน 4 → bu2
    - 一 yī: ปกติ yi1; ถ้าหน้าคำโทน 4 → yi2; ถ้าหน้าคำ non-4 → yi4
    """
    out = syllables[:]
    for i, syl in enumerate(out[:-1]):
        nxt = out[i+1]
        if len(syl) < 2 or len(nxt) < 2:
            continue
        if syl.startswith('bu') and syl[-1] in '1234' and nxt[-1] == '4':
            out[i] = 'bu2'
        if syl.startswith('yi') and syl[-1] in '1234':
            out[i] = 'yi2' if nxt[-1] == '4' else 'yi4'
    return out

# ---------- ช่วยตัดคำ + รวมพยางค์ให้ "ติดกันในคำ" ----------
_HAN_RE = re.compile(r'[\u3400-\u9FFF\uF900-\uFAFF]')
def _is_han(ch: str) -> bool:
    return bool(_HAN_RE.match(ch))

def _words_joined_pinyin(text: str, syllables: List[str], words: List[str]) -> Tuple[List[str], str]:
    """
    คืน (word_level_list, pinyin_line)
    - word_level_list: พินอินต่อคำ โดยพยางค์ในคำ 'ติดกัน' (เช่น 'xi3huan1')
    - pinyin_line: join แต่ละคำด้วยช่องว่างเดียว ('wo3 xi3huan1 ni3')
    """
    idx = 0
    word_list: List[str] = []
    for w in words:
        n = sum(1 for ch in w if _is_han(ch))
        if n > 0:
            seg = syllables[idx: idx + n]
            idx += n
            word_list.append("".join(seg))  # พยางค์ติดกันในคำ
        else:
            word_list.append(w)             # เครื่องหมาย/เว้นวรรคคงเดิม
    return word_list, " ".join(word_list)

# ---------- ฟังก์ชันหลัก (คืนทั้ง numbers + marks ในครั้งเดียว) ----------
def convert_pinyin_both(
    text: str,
    use_sandhi: bool = False
) -> Dict:
    """
    แปลงภาษาจีนเป็นพินอินรูปแบบ:
    {
      "input": "...",
      "tone_numbers": { "pinyin": "...", "syllables": [...] },
      "tone_marks":   { "pinyin": "...", "syllables": [...] }
    }
    โดยพยางค์ภายใน 'คำ' จะถูกต่อให้ติดกัน (เช่น xi3huan1 / xǐhuān)
    """
    # 1) g2pM → tone numbers
    syl_num = _g2p(text, tone=True)

    # 2) sandhi (ถ้าต้องการ)
    if use_sandhi:
        syl_num = apply_basic_sandhi(syl_num)

    # 3) tone marks
    syl_mark = [number_to_mark(s) for s in syl_num]

    # 4) ตัดคำ แล้วรวมพยางค์ให้ติดกันภายในคำ
    words = jieba.lcut(text)
    words_num,  line_num  = _words_joined_pinyin(text, syl_num,  words)  # ["wo3","xi3huan1","ni3"], "wo3 xi3huan1 ni3"
    words_mark, line_mark = _words_joined_pinyin(text, syl_mark, words)  # ["wǒ","xǐhuān","nǐ"],    "wǒ xǐhuān nǐ"

    # 5) คืนผลตามฟอร์แมตที่ต้องการ
    return {
        "input": text,
        "tone_numbers": {
            "pinyin": line_num,
            "syllables": words_num
        },
        "tone_marks": {
            "pinyin": line_mark,
            "syllables": words_mark
        }
    }
