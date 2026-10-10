"""Score OCR transcriptions against a reference transcription.

The methods disagree about reading order (NDL interleaves furigana and jumps
between text blocks), so a strict edit distance would mostly measure layout.
Instead this reports order-insensitive overlap of characters and of character
bigrams. Bigrams still reward getting runs of text right, so a method can't
score well by emitting the right characters in random order.

Furigana (written 漢字《かな》 in the Claude/reference format) is dropped before
comparison, because NDL sometimes emits it as separate lines and sometimes not.

Usage:
    python3 -I scripts/score_ocr.py REFERENCE.txt NAME=CANDIDATE.txt [NAME=CANDIDATE.txt ...]
"""
import re
import sys
from collections import Counter
from pathlib import Path

KEEP = re.compile(r"[぀-ヿ㐀-鿿〳〴〵ゝゞヽヾ々〆]")


def normalize(text: str) -> str:
    text = text.split("## notes")[0]                        # drop notes before headers go
    text = re.sub(r"^##.*$", "", text, flags=re.M)          # section headers
    text = re.sub(r"^\[[a-z]+\]\s*", "", text, flags=re.M)  # [main] [caption] tags
    text = re.sub(r"《[^》]*》", "", text)                    # furigana
    text = re.sub(r"〔([^〕?]*)\?〕", r"\1", text)             # keep guessed characters
    text = text.replace("〴〵", "〳〵")
    return "".join(KEEP.findall(text))


def overlap(ref: Counter, cand: Counter) -> tuple[float, float, float]:
    hit = sum((ref & cand).values())
    p = hit / max(1, sum(cand.values()))
    r = hit / max(1, sum(ref.values()))
    f = 2 * p * r / max(1e-9, p + r)
    return p, r, f


def bigrams(s: str) -> Counter:
    return Counter(s[i:i + 2] for i in range(len(s) - 1))


def score(ref_text: str, cand_text: str) -> dict:
    ref, cand = normalize(ref_text), normalize(cand_text)
    cp, cr, cf = overlap(Counter(ref), Counter(cand))
    bp, br, bf = overlap(bigrams(ref), bigrams(cand))
    return {"ref_chars": len(ref), "cand_chars": len(cand),
            "char_P": cp, "char_R": cr, "char_F": cf, "bigram_F": bf}


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    ref_text = Path(sys.argv[1]).read_text(encoding="utf-8")
    print(f"{'method':<14}{'chars':>7}{'char P':>8}{'char R':>8}{'char F':>8}{'bigram F':>10}")
    for arg in sys.argv[2:]:
        name, path = arg.split("=", 1)
        s = score(ref_text, Path(path).read_text(encoding="utf-8"))
        print(f"{name:<14}{s['cand_chars']:>7}{s['char_P']:>8.2f}{s['char_R']:>8.2f}"
              f"{s['char_F']:>8.2f}{s['bigram_F']:>10.2f}   (ref {s['ref_chars']} chars)")
