"""Decide which scan each page of the book is transcribed from.

The NDL copy (sharper, original binding) is the primary source. The Waseda
copy is a rebinding of the same four 編 and contains at least one leaf the
NDL copy lacks, so every Waseda half-page is matched (by OCR text bigrams)
against every NDL half-page; Waseda halves with text and no good NDL match
are added to the plan.

Halves are split at the book's fold (split_pages.book_midpoint). Matching
uses NDL OCR ver.3 line boxes and Lite text.

Writes ocr/page_plan.tsv, in reading order:
    order  source  vol  page  pages  chars  note
where `pages` is R, L or RL (which halves of that scan to transcribe).

Usage:  python3 -I scripts/page_plan.py
"""
import json
import re
import sys
from collections import Counter
from pathlib import Path

from PIL import Image, ImageOps

sys.path.insert(0, str(Path(__file__).resolve().parent))
from split_pages import book_midpoint  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
V3 = ROOT / "ocr" / "ndl_v3"
SCANS = {"ndl": ROOT / "童絵解万国噺 (1861) - NDL 207-1695",
         "waseda": ROOT / "童絵解万国噺 (1861) - Waseda 文庫11 a0380"}
JP = re.compile(r"[぀-ヿ㐀-鿿]")
MIN_CHARS = 15      # a half with fewer OCR characters has no real text
MATCH = 0.45        # bigram Dice score above which two halves are the same leaf


def halves(source: str, vol: str, page: str) -> dict[str, str]:
    d = json.loads((V3 / f"{source}_{vol}" / "json" / f"{page}.json").read_text(encoding="utf-8"))
    img = Image.open(SCANS[source] / vol / f"{page}.jpg")
    mid = book_midpoint(ImageOps.grayscale(img))
    out = {"R": "", "L": ""}
    for x0, y0, x1, y1, text in d["contents"]:
        out["R" if (x0 + x1) / 2 >= mid else "L"] += "".join(JP.findall(text))
    return out


def grams(s: str) -> Counter:
    return Counter(s[i:i + 2] for i in range(len(s) - 1))


def dice(a: Counter, b: Counter) -> float:
    return 2 * sum((a & b).values()) / max(1, sum(a.values()) + sum(b.values()))


def scans(source: str):
    for vol_dir in sorted(SCANS[source].glob("vol*")):
        for p in sorted(vol_dir.glob("p*.jpg")):
            yield vol_dir.name, p.stem


ndl = {(v, p): halves("ndl", v, p) for v, p in scans("ndl")}
ndl_grams = [(k, side, grams(t)) for k, h in ndl.items() for side, t in h.items() if len(t) >= MIN_CHARS]

rows = []
for (v, p), h in ndl.items():
    sides = "".join(s for s in "RL" if len(h[s]) >= MIN_CHARS)
    rows.append(["ndl", v, p, sides, sum(len(h[s]) for s in sides), ""])

extra = []
for v, p in scans("waseda"):
    h = halves("waseda", v, p)
    for side in "RL":
        if len(h[side]) < MIN_CHARS:
            continue
        g = grams(h[side])
        best = max(((dice(g, ng), k, s) for k, s, ng in ndl_grams), default=(0, None, None))
        if best[0] < MATCH:
            extra.append(["waseda", v, p, side, len(h[side]),
                          f"not in NDL copy (best match {best[0]:.2f} = ndl {best[1]} {best[2]})"])

out = ROOT / "ocr" / "page_plan.tsv"
with out.open("w", encoding="utf-8") as f:
    f.write("order\tsource\tvol\tpage\tpages\tchars\tnote\n")
    for i, r in enumerate(rows + extra, 1):
        f.write("\t".join(map(str, [i, *r])) + "\n")
text_spreads = sum(1 for r in rows if r[3])
print(f"{out}: {text_spreads} NDL spreads with text ({len(rows)} scans), "
      f"{len(extra)} Waseda half-pages not in the NDL copy")
for r in extra:
    print("  waseda", *r[1:])
