"""Score every OCR method on every sample spread that has a reference.

References live in ocr/reference/<vol>_<page>.txt. For each, the candidate
outputs of each method are located (Waseda scan, and the matching spread of
the NDL copy via SAMPLES below) and scored with score_ocr.score().
Prints a per-spread table and a character-weighted total per method.

Usage:  python3 -I scripts/eval_all.py
"""
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from score_ocr import score  # noqa: E402

ROOT = Path(__file__).resolve().parent.parent
OCR = ROOT / "ocr"

# Waseda spread -> matching NDL-copy spread (from ocr/copy_map.tsv, checked by eye).
SAMPLES = {
    ("vol1", "p0005"): ("vol2", "p0005"),   # NDL copy matches only the left page
    ("vol1", "p0009"): ("vol1", "p0008"),
    ("vol1", "p0020"): ("vol1", "p0019"),
    ("vol2", "p0014"): ("vol3", "p0013"),
    ("vol2", "p0029"): ("vol4", "p0011"),
}


def candidates(wvol: str, wpage: str, nvol: str, npage: str) -> dict[str, Path]:
    return {
        "v3 · Waseda": OCR / "ndl_v3" / f"waseda_{wvol}" / "txt" / f"{wpage}_main.txt",
        "v3 · NDL": OCR / "ndl_v3" / f"ndl_{nvol}" / "txt" / f"{npage}_main.txt",
        "Lite · Waseda": OCR / "ndl" / wvol / f"{wpage}.clean.txt",
        "Lite · NDL": OCR / "ndl_lite_ndlcopy" / nvol / f"{npage}.clean.txt",
        "Claude eye": OCR / "claude" / f"{wvol}_{wpage}.txt",
        "Light pass": OCR / "lightpass" / f"{wvol}_{wpage}.txt",
    }


totals = defaultdict(lambda: [0, 0.0, 0.0])  # ref chars, weighted char F, weighted bigram F
for (wvol, wpage), (nvol, npage) in SAMPLES.items():
    ref_path = OCR / "reference" / f"{wvol}_{wpage}.txt"
    if not ref_path.exists():
        continue
    ref = ref_path.read_text(encoding="utf-8")
    print(f"\n{wvol} {wpage}  (NDL copy {nvol} {npage})")
    print(f"  {'method':<15}{'chars':>6}{'char P':>8}{'char R':>8}{'char F':>8}{'bigram F':>10}")
    for name, path in candidates(wvol, wpage, nvol, npage).items():
        if not path.exists():
            continue
        s = score(ref, path.read_text(encoding="utf-8"))
        print(f"  {name:<15}{s['cand_chars']:>6}{s['char_P']:>8.2f}{s['char_R']:>8.2f}"
              f"{s['char_F']:>8.2f}{s['bigram_F']:>10.2f}")
        t = totals[name]
        t[0] += s["ref_chars"]
        t[1] += s["char_F"] * s["ref_chars"]
        t[2] += s["bigram_F"] * s["ref_chars"]
    print(f"  reference: {s['ref_chars']} chars")

print("\nAll scored spreads (weighted by reference length):")
print(f"  {'method':<15}{'char F':>8}{'bigram F':>10}")
for name, (n, cf, bf) in sorted(totals.items(), key=lambda kv: -kv[1][2] / max(1, kv[1][0])):
    print(f"  {name:<15}{cf / n:>8.2f}{bf / n:>10.2f}")
