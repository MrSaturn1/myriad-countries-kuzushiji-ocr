"""Drop obvious noise lines from NDL Kotenseki OCR output.

The detector sometimes reads illustration hatching as text, producing lines
like 訓訓訓訓…, □□□□…, ■10, TEL, HI.  This keeps only lines that look like
Japanese text.  It does not fix reading order or misread characters.

Usage:
    python3 -I scripts/clean_ndl.py IN.txt [IN.txt ...]   # writes IN.clean.txt
"""
import re
import sys
from collections import Counter
from pathlib import Path

JP = re.compile(r"[぀-ヿ㐀-鿿〳〵ゝゞ々]")


def is_noise(line: str) -> bool:
    s = line.strip()
    if not s:
        return True
    jp = JP.findall(s)
    if len(jp) / len(s) < 0.6:          # mostly □, ■, latin, digits, symbols
        return True
    top, n = Counter(s).most_common(1)[0]
    if len(s) >= 6 and n / len(s) > 0.5:  # one character repeated (訓訓訓…)
        return True
    return False


for p in map(Path, sys.argv[1:]):
    lines = p.read_text(encoding="utf-8").splitlines()
    kept = [l.strip() for l in lines if not is_noise(l)]
    p.with_suffix(".clean.txt").write_text("\n".join(kept) + "\n", encoding="utf-8")
    print(f"{p.parent.name}/{p.name}: kept {len(kept)}/{len(lines)} lines")
