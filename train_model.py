import math
import random
from typing import List, Tuple, Dict

import torch
from torch import nn
from torch.nn.utils.rnn import pad_sequence, pack_padded_sequence, pad_packed_sequence
from torch.utils.data import Dataset, DataLoader


# -----------------------------
# 1) Helper: Pinyin numeric tone -> tone mark
# -----------------------------

TONE_MARKS = {
    "a": "āáǎàa",
    "e": "ēéěèe",
    "i": "īíǐìi",
    "o": "ōóǒòo",
    "u": "ūúǔùu",
    "ü": "ǖǘǚǜü",
}

VOWELS = set("aeiouü")


def convert_syllable_num_to_tone(s: str) -> str:
    """
    แปลงพยางค์พินอินที่มีเลขโทน (เช่น 'hao3')
    เป็นแบบมีวรรณยุกต์ ('hǎo')
    """
    if not s:
        return s

    # หาเลขโทน
    tone = 0
    base = ""
    for ch in s:
        if ch.isdigit():
            tone = int(ch)
        else:
            base += ch

    if tone <= 0 or tone > 4:
        return base  # โทน 0/5 หรือไม่มีเลข → ไม่มีวรรณยุกต์

    # กฎตำแหน่งวรรณยุกต์: a > e > o, ถ้าไม่มี → ตัวสระตัวแรก
    idx = -1
    for pri in ["a", "e", "o"]:
        idx = base.find(pri)
        if idx != -1:
            break
    if idx == -1:
        # fallback: สระตัวแรก
        for i, ch in enumerate(base):
            if ch in VOWELS:
                idx = i
                break
    if idx == -1:
        # ไม่มีสระเลย
        return base

    vowel = base[idx]
    marks = TONE_MARKS.get(vowel, None)
    if not marks:
        # เผื่อมี 'v' ใช้แบบ ü
        marks = TONE_MARKS["ü"]
    marked_vowel = marks[tone - 1]

    return base[:idx] + marked_vowel + base[idx + 1 :]


def convert_line_num_to_tone(line: str) -> str:
    """
    แปลงทั้งบรรทัดจากเลขโทน → วรรณยุกต์
    เช่น: "ni3 hao3 shi4 jie4" -> "nǐ hǎo shì jiè"
    """
    tokens = line.strip().split()
    return " ".join(convert_syllable_num_to_tone(tok) for tok in tokens)


# -----------------------------
# 2) Dataset
# -----------------------------


class ZHPinyinDataset(Dataset):
    """
    รูปแบบไฟล์ที่คาดหวัง: TSV มี 2 คอลัมน์

    han<TAB>pinyin_numeric

    ตัวอย่าง:
    你好世界    ni3 hao3 shi4 jie4

    - han: ประโยคจีนตัวย่อ
    - pinyin_numeric: พินอินเว้น space แบบมีเลขโทน

    โค้ดจะ:
      * แปลงเป็นพินอินแบบมีวรรณยุกต์
      * align ตัวอักษรจีนแต่ละตัวกับ 1 พยางค์พินอิน (1:1)
    """

    PAD = "<PAD>"
    UNK = "<UNK>"

    def __init__(
        self,
        path: str,
        char2id: Dict[str, int] = None,
        py2id: Dict[str, int] = None,
        build_vocab: bool = True,
        max_len: int = 64,
    ):
        self.samples: List[Tuple[List[int], List[int], int]] = []
        self.max_len = max_len

        raw_samples: List[Tuple[List[str], List[str]]] = []

        with open(path, encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or "\t" not in line:
                    continue
                han, py = line.split("\t", 1)
                han = han.strip()
                py = py.strip()
                if not han or not py:
                    continue

                # แปลงจากเลขโทนเป็นวรรณยุกต์
                py_toned = convert_line_num_to_tone(py)
                py_tokens = py_toned.split()

                chars = list(han)
                if len(chars) != len(py_tokens):
                    # ถ้า align ไม่ตรง ข้ามไปเลย (เพื่อให้ง่าย)
                    continue

                # ตัดให้ไม่เกิน max_len
                if len(chars) > max_len:
                    chars = chars[:max_len]
                    py_tokens = py_tokens[:max_len]

                raw_samples.append((chars, py_tokens))

        # สร้าง vocab ถ้าต้องการ
        if build_vocab:
            char_vocab = {self.PAD: 0, self.UNK: 1}
            py_vocab = {self.PAD: 0}

            for chars, pys in raw_samples:
                for ch in chars:
                    if ch not in char_vocab:
                        char_vocab[ch] = len(char_vocab)
                for syl in pys:
                    if syl not in py_vocab:
                        py_vocab[syl] = len(py_vocab)

            self.char2id = char_vocab
            self.py2id = py_vocab
        else:
            assert char2id is not None and py2id is not None
            self.char2id = char2id
            self.py2id = py2id

        # encode ตัวอย่างเป็น id
        for chars, pys in raw_samples:
            x = [self.char2id.get(ch, self.char2id[self.UNK]) for ch in chars]
            y = [self.py2id.get(syl, 0) for syl in pys]  # pinyin ที่ไม่รู้ → PAD (0)
            L = len(x)
            self.samples.append((x, y, L))

    def __len__(self):
        return len(self.samples)

    def __getitem__(self, idx):
        return self.samples[idx]


def collate_fn(batch, pad_idx: int = 0):
    """
    collate สำหรับ DataLoader
    batch: list ของ (x_ids, y_ids, length)
    """
    xs, ys, lens = zip(*batch)
    lens = torch.tensor(lens, dtype=torch.long)

    xs = [torch.tensor(x, dtype=torch.long) for x in xs]
    ys = [torch.tensor(y, dtype=torch.long) for y in ys]

    xs_pad = pad_sequence(xs, batch_first=True, padding_value=pad_idx)
    ys_pad = pad_sequence(ys, batch_first=True, padding_value=pad_idx)

    return xs_pad, ys_pad, lens


# -----------------------------
# 3) Model: BiLSTM tagger (ดู context → รองรับ polyphonic)
# -----------------------------


class BiLSTMPinyinTagger(nn.Module):
    def __init__(
        self,
        vocab_size: int,
        tagset_size: int,
        emb_dim: int = 128,
        hidden_dim: int = 256,
        pad_idx: int = 0,
    ):
        super().__init__()
        self.embedding = nn.Embedding(vocab_size, emb_dim, padding_idx=pad_idx)
        self.lstm = nn.LSTM(
            emb_dim,
            hidden_dim // 2,
            batch_first=True,
            bidirectional=True,
            num_layers=1,
        )
        self.fc = nn.Linear(hidden_dim, tagset_size)

    def forward(self, x, lengths):
        # x: (B, T)
        emb = self.embedding(x)  # (B, T, E)

        packed = pack_padded_sequence(
            emb, lengths.cpu(), batch_first=True, enforce_sorted=False
        )
        packed_out, _ = self.lstm(packed)
        out, _ = pad_packed_sequence(packed_out, batch_first=True)  # (B, T, H)

        logits = self.fc(out)  # (B, T, C)
        return logits


# -----------------------------
# 4) Training loop
# -----------------------------


def train_model(
    train_path: str,
    dev_path: str = None,
    max_len: int = 64,
    batch_size: int = 32,
    epochs: int = 10,
    lr: float = 1e-3,
    device: str = None,
):
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    # dataset เทรน + สร้าง vocab
    train_ds = ZHPinyinDataset(train_path, max_len=max_len, build_vocab=True)

    # dataset dev ใช้ vocab เดียวกัน
    if dev_path:
        dev_ds = ZHPinyinDataset(
            dev_path,
            char2id=train_ds.char2id,
            py2id=train_ds.py2id,
            build_vocab=False,
            max_len=max_len,
        )
    else:
        dev_ds = None

    pad_idx = train_ds.char2id[ZHPinyinDataset.PAD]

    train_loader = DataLoader(
        train_ds,
        batch_size=batch_size,
        shuffle=True,
        collate_fn=lambda b: collate_fn(b, pad_idx=pad_idx),
    )

    if dev_ds:
        dev_loader = DataLoader(
            dev_ds,
            batch_size=batch_size,
            shuffle=False,
            collate_fn=lambda b: collate_fn(b, pad_idx=pad_idx),
        )
    else:
        dev_loader = None

    model = BiLSTMPinyinTagger(
        vocab_size=len(train_ds.char2id),
        tagset_size=len(train_ds.py2id),
        pad_idx=pad_idx,
    ).to(device)

    criterion = nn.CrossEntropyLoss(ignore_index=train_ds.py2id[ZHPinyinDataset.PAD])
    optimizer = torch.optim.Adam(model.parameters(), lr=lr)

    for epoch in range(1, epochs + 1):
        model.train()
        total_loss = 0.0
        total_tok = 0

        for xs, ys, lens in train_loader:
            xs = xs.to(device)
            ys = ys.to(device)
            lens = lens.to(device)

            optimizer.zero_grad()
            logits = model(xs, lens)  # (B, T, C)

            B, T, C = logits.shape
            loss = criterion(logits.view(B * T, C), ys.view(B * T))
            loss.backward()
            optimizer.step()

            # สถิติ
            with torch.no_grad():
                mask = ys.ne(train_ds.py2id[ZHPinyinDataset.PAD])
                n_tok = mask.sum().item()
                total_tok += n_tok
                total_loss += loss.item() * n_tok

        avg_loss = total_loss / max(total_tok, 1)
        print(f"Epoch {epoch}: train loss {avg_loss:.4f}")

        # ประเมินบน dev แบบง่าย ๆ
        if dev_loader:
            model.eval()
            correct = 0
            total = 0
            with torch.no_grad():
                for xs, ys, lens in dev_loader:
                    xs = xs.to(device)
                    ys = ys.to(device)
                    lens = lens.to(device)

                    logits = model(xs, lens)  # (B, T, C)
                    preds = logits.argmax(dim=-1)

                    mask = ys.ne(train_ds.py2id[ZHPinyinDataset.PAD])
                    correct += (preds.eq(ys) & mask).sum().item()
                    total += mask.sum().item()
            acc = correct / max(total, 1)
            print(f"           dev token accuracy: {acc:.4f}")

    return model, train_ds.char2id, train_ds.py2id


# -----------------------------
# 5) Inference helper
# -----------------------------


def decode_pinyin_ids(ids: List[int], id2py: Dict[int, str]) -> str:
    """
    แปลง list ของ pinyin ID -> ประโยคพินอิน (เว้นวรรคเป็นพยางค์)
    """
    toks = []
    for i in ids:
        if i == 0:
            continue  # ข้าม PAD
        toks.append(id2py.get(i, ""))
    return " ".join(toks)


def predict_sentence(
    model: nn.Module,
    sentence: str,
    char2id: Dict[str, int],
    id2py: Dict[int, str],
    device: str = None,
    max_len: int = 64,
) -> str:
    if device is None:
        device = "cuda" if torch.cuda.is_available() else "cpu"

    model.eval()

    chars = list(sentence.strip())
    if len(chars) > max_len:
        chars = chars[:max_len]

    x = [char2id.get(ch, char2id[ZHPinyinDataset.UNK]) for ch in chars]
    lens = torch.tensor([len(x)], dtype=torch.long)
    xs = torch.tensor([x], dtype=torch.long)

    xs = xs.to(device)
    lens = lens.to(device)

    with torch.no_grad():
        logits = model(xs, lens)  # (1, T, C)
        preds = logits.argmax(dim=-1)[0].cpu().tolist()  # (T,)

    return decode_pinyin_ids(preds, id2py)


# ตัวอย่างการใช้งานหลังเทรนเสร็จ
if __name__ == "__main__":
    # เทรนโมเดล
    model, char2id, py2id = train_model("train.tsv", "dev.tsv", epochs=5)
    id2py = {v: k for k, v in py2id.items()}

    # === NEW: บันทึกโมเดล + vocab ลงไฟล์ ===
    save_path = "model/model.p"  # หรือจะใช้ชื่อ model.p ก็ได้
    torch.save({
        "model_state_dict": model.state_dict(),
        "char2id": char2id,
        "py2id": py2id,
    }, save_path)

    print(f"Model saved to {save_path}")

    # ทดสอบประโยคตัวอย่าง
    sent = "今天天气很好"
    py_sent = predict_sentence(model, sent, char2id, id2py)
    print(sent, "->", py_sent)

