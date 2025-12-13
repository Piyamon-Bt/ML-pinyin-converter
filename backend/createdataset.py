from pypinyin import pinyin, Style

input_path = "data/raw.txt"
output_path = "data/base.tsv"

with open(input_path, encoding="utf-8") as fin, open(output_path, "w", encoding="utf-8") as fout:
    for line in fin:
        han = line.strip()
        if not han:
            continue
        # ใช้ TONE3 => พินอินมีเลขโทน เช่น ni3 hao3
        py_list = pinyin(han, style=Style.TONE3, strict=False)
        # py_list เป็น list ของ list เช่น [['jin1'], ['tian1'], ...]
        py_tokens = [item[0] for item in py_list]
        py_line = " ".join(py_tokens)
        fout.write(f"{han}\t{py_line}\n")

print("Saved to", output_path)
