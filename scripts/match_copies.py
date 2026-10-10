"""Match each Waseda spread to the same spread in the NDL copy.

Uses the NDL OCR ver.3 text of both copies: the NDL spread sharing the most
character bigrams with a Waseda spread is taken as its counterpart. Writes
ocr/copy_map.tsv: waseda_vol, page, ndl_vol, page, score (0–1).

Usage:  python3 -I scripts/match_copies.py
"""
import re
from collections import Counter
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
V3 = ROOT / "ocr" / "ndl_v3"
JP = re.compile(r"[぀-ヿ㐀-鿿]")


def grams(path: Path) -> Counter:
    s = "".join(JP.findall(path.read_text(encoding="utf-8")))
    return Counter(s[i:i + 2] for i in range(len(s) - 1))


def pages(book: str) -> dict[str, Counter]:
    return {p.name.split("_")[0]: grams(p) for p in sorted((V3 / book / "txt").glob("p*_main.txt"))}


ndl = {f"ndl_vol{i}": pages(f"ndl_vol{i}") for i in range(1, 5)}
rows = []
for wvol in ("waseda_vol1", "waseda_vol2"):
    for wp, wg in pages(wvol).items():
        best = (0.0, "", "")
        if sum(wg.values()) >= 20:  # covers / blank pages have no text to match
            for nvol, np_ in ndl.items():
                for npage, ng in np_.items():
                    s = 2 * sum((wg & ng).values()) / max(1, sum(wg.values()) + sum(ng.values()))
                    best = max(best, (s, nvol, npage))
        rows.append(f"{wvol}\t{wp}\t{best[1]}\t{best[2]}\t{best[0]:.2f}")
out = ROOT / "ocr" / "copy_map.tsv"
out.write_text("waseda_vol\tpage\tndl_vol\tpage\tscore\n" + "\n".join(rows) + "\n", encoding="utf-8")
print(out)
