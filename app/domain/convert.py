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
    # เคสพิเศษมาตรฐานพินอิน
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
    """'wo3' -> 'wǒ', 'lv4'/'lü4' -> 'lǜ'; ถ้าเป็น neutral (ลงท้าย 5/0/ไม่มีเลข) → คืน base ไม่มีโทน"""
    if not syl:
        return syl
    tone = syl[-1]
    base = syl[:-1] if tone in '0123456789' else syl
    base = (base.replace('u:', 'ü').replace('U:', 'Ü')
                 .replace('v', 'ü').replace('V', 'Ü'))
    if tone not in '1234':  # neutral หรือเลขอื่นที่ไม่ใช่ 1..4
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

# ---------- ยูทิลสำหรับ sandhi ----------
_HAN_RE = re.compile(r'[\u3400-\u9FFF\uF900-\uFAFF]')
def _is_han(ch: str) -> bool:
    return bool(_HAN_RE.match(ch))

def _strip_tone(s: str) -> str:
    """ตัดเลขโทนท้ายพยางค์ และ normalize ü"""
    if not s: return s
    base = s[:-1] if s[-1] in '0123456789' else s
    base = (base.replace('u:', 'ü').replace('U:', 'Ü')
                 .replace('v', 'ü').replace('V', 'Ü'))
    return base

NEUTRAL_SET = set(list("的地得了吗呢吧啊着过過們们子頭头"))
# หมายเหตุ: รวมรูปตัวเต็ม/ตัวย่อที่พบบ่อย

def _assimilation_a(prev_base_lower: str) -> str:
    """กลืนเสียง '啊' เป็น ya/wa/na/nga ตามตัวก่อนหน้า (approx.)"""
    if not prev_base_lower:
        return 'a5'
    if prev_base_lower.endswith('ng'):
        return 'nga5'
    if prev_base_lower.endswith('n'):
        return 'na5'
    if prev_base_lower[-1] in ('a','e','o'):
        return 'wa5'
    if prev_base_lower[-1] in ('i','ü','u'):
        return 'ya5' if prev_base_lower[-1] in ('i','ü') else 'wa5'
    return 'a5'

def apply_extended_sandhi(text: str, syllables: List[str]) -> List[str]:
    """
    กฎ sandhi ที่รองรับ:
      - 3+3 → 2+3 (ซ้าย→ขวา)
      - 不 → bu2 เมื่อหน้าคำเสียง 4
      - 一 → yi2 เมื่อหน้าคำเสียง 4, มิฉะนั้น yi4 (กรณีเลขเดี่ยว/อ่านตัวเลขเดี่ยว ๆ ไม่บังคับ)
      - 轻声 (neutral) → เติมเลข 5 ให้พยางค์: 的 地 得 了 吗 呢 吧 啊 着 过/過 们/們 子 头/頭 ฯลฯ
      - '啊' กลืนเสียงเป็น ya/wa/na/nga และติดเลข 5
    """
    out = syllables[:]  # ทำงานบนสำเนา
    # สร้างลิสต์ตัวจีน (เฉพาะตัวที่ map กับพยางค์)
    han_chars = [ch for ch in text if _is_han(ch)]
    n = min(len(han_chars), len(out))

    # --- 3+3 → 2+3 (เดินซ้าย→ขวา) ---
    i = 0
    while i < n - 1:
        if out[i] and out[i][-1] == '3' and out[i+1] and out[i+1][-1] == '3':
            out[i] = _strip_tone(out[i]) + '2'   # เปลี่ยนตัวหน้าเป็น tone 2
        i += 1

    # --- 不 / 一 / 轻声 / อะซิมิเลชันของ '啊' ---
    for k in range(n):
        ch = han_chars[k]
        cur = out[k] if k < len(out) else ''
        nxt_tone = out[k+1][-1] if k+1 < n and out[k+1] else None
        prev_base_lower = _strip_tone(out[k-1]).lower() if k-1 >= 0 else ''

        # 不: หน้าคำโทน 4 → bu2
        if ch == '不':
            if nxt_tone == '4':
                out[k] = 'bu2'
            else:
                # กรณีอื่นคง bu4 (ถ้า g2pM ให้ bu4 มาตาม dict)
                base = _strip_tone(cur) or 'bu'
                tone = cur[-1] if cur and cur[-1] in '1234' else '4'
                out[k] = base + tone
            continue

        # 一: หน้าคำโทน 4 → yi2; หน้าคำ 1/2/3 → yi4
        if ch == '一':
            # ถ้าถัดไปเป็นโทน 4 ⇒ yí (2), มิฉะนั้น ⇒ yì (4)
            if nxt_tone == '4':
                out[k] = 'yi2'
            elif nxt_tone in ('1', '2', '3'):
                out[k] = 'yi4'
            else:
                # ถ้าไม่ชัด (เช่น ลงท้าย/เดี่ยวๆ) ให้คงตาม dict เดิม
                base = _strip_tone(cur) or 'yi'
                tone = cur[-1] if cur and cur[-1] in '1234' else '1'
                out[k] = base + tone
            continue

        # 轻声 (neutral) สำหรับคำช่วย/ปัจจัยที่พบได้บ่อย → ผูกเลข 5
        if ch in NEUTRAL_SET:
            if ch == '啊':
                out[k] = _assimilation_a(prev_base_lower)  # ya5/wa5/na5/nga5
            else:
                out[k] = _strip_tone(cur) + '5'            # เช่น men5, de5, ba5
            continue

    return out

# ---------- ช่วยตัดคำ + รวมพยางค์ให้ "ติดกันในคำ" ----------
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
    {
      "input": "...",
      "tone_numbers": { "pinyin": "...", "syllables": [...] },
      "tone_marks":   { "pinyin": "...", "syllables": [...] }
    }
    - ถ้า use_sandhi=True จะใช้กฎ: 3+3→2+3, 不/一, 轻声(เลข 5), '啊' กลืนเสียง
    - พยางค์ภายใน 'คำ' จะถูกต่อให้ติดกัน (เช่น xi3huan1 / xǐhuān)
    """
    # 1) g2pM → tone numbers
    syl_num = _g2p(text, tone=True)

    # 2) sandhi (ถ้าต้องการ)
    if use_sandhi:
        syl_num = apply_extended_sandhi(text, syl_num)

    # 3) tone marks (จากผลหลัง sandhi)
    syl_mark = [number_to_mark(s) for s in syl_num]

    # 4) ตัดคำ แล้วรวมพยางค์ให้ติดกันภายในคำ
    words = jieba.lcut(text)
    words_num,  line_num  = _words_joined_pinyin(text, syl_num,  words)
    words_mark, line_mark = _words_joined_pinyin(text, syl_mark, words)

    # 5) คืนผล
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
