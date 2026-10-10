"""Merge NDL OCR Lite (better characters) into NDL OCR ver.3's reading order.

For one scan, ver.3 lists text lines in reading order with boxes; Lite lists
lines with boxes but in a jumbled order and with more accurate characters.
Each ver.3 line is paired with the Lite line whose box overlaps it most; the
merged draft keeps ver.3's order and shows both readings where they differ.
Lite lines that no ver.3 line claims (often captions, labels or furigana) are
kept at the end with their position, so nothing is silently dropped.

Output is a TSV the correction pass works through, one row per line:
    n  status  x0 y0 x1 y1  lite_text  v3_text
status: same | diff | v3only | liteonly | noise
Coordinates are in pixels of the scan the OCR ran on.

Usage:
    python3 -I scripts/merge_ocr.py LITE.json V3.json OUT.tsv
"""
import json
import re
import sys
from difflib import SequenceMatcher
from pathlib import Path

JP = re.compile(r"[぀-ヿ㐀-鿿〳〵ゝゞ々]")


def is_noise(text: str) -> bool:
    s = text.strip()
    if not s:
        return True
    if len(JP.findall(s)) / len(s) < 0.6:
        return True
    top = max(s.count(c) for c in set(s))
    return len(s) >= 6 and top / len(s) > 0.5


def lite_lines(path: Path) -> list[dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    out = []
    for group in d["contents"]:
        for ln in group:
            xs = [p[0] for p in ln["boundingBox"]]
            ys = [p[1] for p in ln["boundingBox"]]
            out.append({"box": (min(xs), min(ys), max(xs), max(ys)), "text": ln["text"],
                        "conf": float(ln.get("confidence") or 0)})
    # Lite sometimes emits a line twice (a fragment inside a longer line):
    # drop lines mostly contained in a longer one.
    out.sort(key=lambda l: -len(l["text"]))
    kept = []
    for ln in out:
        if any(contained(ln["box"], k["box"]) > 0.8 and k["text"].find(ln["text"][:2]) >= 0 for k in kept):
            continue
        kept.append(ln)
    return kept


def v3_lines(path: Path) -> list[dict]:
    d = json.loads(path.read_text(encoding="utf-8"))
    return [{"box": tuple(c[:4]), "text": c[4]} for c in d["contents"]]


def area(b):
    return max(0, b[2] - b[0]) * max(0, b[3] - b[1])


def inter(a, b):
    return area((max(a[0], b[0]), max(a[1], b[1]), min(a[2], b[2]), min(a[3], b[3])))


def contained(a, b) -> float:
    """Fraction of box a inside box b."""
    return inter(a, b) / max(1, area(a))


def iou(a, b) -> float:
    i = inter(a, b)
    return i / max(1, area(a) + area(b) - i)


def merge(lite: list[dict], v3: list[dict]) -> list[tuple]:
    rows, used = [], set()
    for n, v in enumerate(v3, 1):
        best, best_s = None, 0.0
        for i, l in enumerate(lite):
            if i in used:
                continue
            s = iou(v["box"], l["box"])
            if s > best_s:
                best, best_s = i, s
        if best is not None and best_s >= 0.3:
            used.add(best)
            l = lite[best]
            same = l["text"] == v["text"]
            status = "same" if same else "diff"
            rows.append((n, status, *v["box"], l["text"], v["text"]))
        else:
            rows.append((n, "noise" if is_noise(v["text"]) else "v3only", *v["box"], "", v["text"]))
    leftovers = [l for i, l in enumerate(lite) if i not in used]
    # Right-to-left, top-to-bottom, the usual order for vertical text.
    leftovers.sort(key=lambda l: (-l["box"][2], l["box"][1]))
    for k, l in enumerate(leftovers, len(rows) + 1):
        status = "noise" if is_noise(l["text"]) else "liteonly"
        rows.append((k, status, *l["box"], l["text"], ""))
    return rows


def similarity(rows) -> float:
    a = "".join(r[6] for r in rows if r[1] in ("same", "diff"))
    b = "".join(r[7] for r in rows if r[1] in ("same", "diff"))
    return SequenceMatcher(None, a, b, autojunk=False).ratio() if a and b else 0.0


if __name__ == "__main__":
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    lite, v3, out = Path(sys.argv[1]), Path(sys.argv[2]), Path(sys.argv[3])
    rows = merge(lite_lines(lite), v3_lines(v3))
    out.parent.mkdir(parents=True, exist_ok=True)
    with out.open("w", encoding="utf-8") as f:
        f.write("n\tstatus\tx0\ty0\tx1\ty1\tlite_text\tv3_text\n")
        for r in rows:
            f.write("\t".join(str(x) for x in r) + "\n")
    counts = {s: sum(1 for r in rows if r[1] == s) for s in ("same", "diff", "v3only", "liteonly", "noise")}
    print(f"{out.name}: {counts}  agreement={similarity(rows):.2f}")
