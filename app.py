# # pip install g2pM
# from g2pM import G2pM
# g2p = G2pM()
# work = input("Input Simplified Chinese: ")
# result = g2p(work, tone=True)  # → ['hang2', 'zhang3', 'xi3', 'huan1', 'yin1', 'yue4'] โดยประมาณ
# print(f"Output = {result}")

# pip install g2pM jieba
from g2pM import G2pM
import jieba
import re

# ---------- number → tone-mark ----------
VOWELS = 'aeiouvüAEIOUVÜ'
TONE_MARKS = {
    'a': ['ā','á','ǎ','à'], 'e': ['ē','é','ě','è'], 'i': ['ī','í','ǐ','ì'],
    'o': ['ō','ó','ǒ','ò'], 'u': ['ū','ú','ǔ','ù'], 'v': ['ǖ','ǘ','ǚ','ǜ'], 'ü': ['ǖ','ǘ','ǚ','ǜ'],
    'A': ['Ā','Á','Ǎ','À'], 'E': ['Ē','É','Ě','È'], 'I': ['Ī','Í','Ǐ','Ì'],
    'O': ['Ō','Ó','Ǒ','Ò'], 'U': ['Ū','Ú','Ǔ','Ù'], 'V': ['Ǖ','Ǘ','Ǚ','Ǜ'], 'Ü': ['Ǖ','Ǘ','Ǚ','Ǜ'],
}
PRIORITY = ['a','e','o']  # a > e > o > (i/u/ü)

def number_to_mark(syl: str) -> str:
    # 'wo3' -> 'wǒ', 'lv4'/ 'lü4' -> 'lǜ'
    if not syl: return syl
    tone = syl[-1]
    base = syl[:-1]
    base = (base.replace('u:', 'ü').replace('U:', 'Ü')
                 .replace('v', 'ü').replace('V', 'Ü'))
    if tone not in '1234':
        return base or syl  # neutral tone → ไม่มีเครื่องหมาย

    # เลือกตำแหน่งวางโทน
    idx = -1
    for p in PRIORITY:
        pos = base.lower().find(p)
        if pos != -1:
            idx = pos; break
    if idx == -1:
        for i, ch in enumerate(base):
            if ch in VOWELS:
                idx = i; break
    if idx == -1:  # ไม่มีสระให้วางโทน
        return syl

    vowel = base[idx]
    table = TONE_MARKS.get(vowel)
    if not table: return syl
    marked = table[int(tone)-1]
    return base[:idx] + marked + base[idx+1:]

# ---------- helpers เดิม ----------
def is_han(ch: str) -> bool:
    return bool(re.match(r'[\u3400-\u9FFF\uF900-\uFAFF]', ch))

def group_pinyin_by_words(text: str, pinyin_syllables: list[str], words: list[str]):
    """
    คืน:
      - word_pairs: list[(คำจีน, "pinyin ของคำ")]
      - word_line: สตริงเว้นวรรคตาม 'คำ' (สองช่องระหว่างคำ)
    """
    idx = 0
    word_pairs, word_pinyins = [], []
    for w in words:
        han_count = sum(1 for ch in w if is_han(ch))
        if han_count > 0:
            group = pinyin_syllables[idx: idx + han_count]
            idx += han_count
            py_word = " ".join(group) if group else ""
            word_pairs.append((w, py_word))
            word_pinyins.append(py_word)
        else:
            word_pairs.append((w, w))
            word_pinyins.append(w)
    return word_pairs, "  ".join(word_pinyins)

# ---------- main ----------
if __name__ == "__main__":
    g2p = G2pM()
    text = input("Input Simplified/Traditional Chinese: ").strip()

    # 1) พยางค์โทนตัวเลข
    syllables_num = g2p(text, tone=True)  # เช่น ['wo3','xi3','huan1',...]

    # 2) แปลงเป็นสระมีโทน
    syllables_mark = [number_to_mark(s) for s in syllables_num]

    # 3) ตัดคำ แล้วจัดกลุ่ม “ตามคำ”
    words = jieba.lcut(text)
    pairs_num,  line_num  = group_pinyin_by_words(text, syllables_num,  words)
    pairs_mark, line_mark = group_pinyin_by_words(text, syllables_mark, words)

    # ------- แสดงผล -------
    print("\n=== Word → Pinyin (tone numbers) ===")
    print(" | ".join([f"{w}:{py}" for w, py in pairs_num]))
    print("\n=== Line (grouped by words, numbers) ===")
    print(line_num)

    print("\n=== Word → Pinyin (tone marks) ===")
    print(" | ".join([f"{w}:{py}" for w, py in pairs_mark]))
    print("\n=== Line (grouped by words, tone marks) ===")
    print(line_mark)
