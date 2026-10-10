"""Split two-page spread scans into single pages, in Japanese reading order.

Each Waseda scan shows an open book: the right-hand page is read first.
Output for a spread `p0009.jpg` is `p0009_R.jpg` (read first) and `p0009_L.jpg`.

The gutter is found by locating the book's outer edges against the grey
background, then taking the darkest vertical band within a few percent of
their midpoint. Searching a wide window instead lets dark illustration
hatching win (vol1 p0020), and a blind 50/50 cut fails because the book is
not always centred in the photo.

Usage:
    python3 -I scripts/split_pages.py OUT_DIR IMAGE [IMAGE ...]
"""
import sys
from pathlib import Path

from PIL import Image, ImageOps

# Overlap kept on each side of the gutter so characters at the fold are not cut.
OVERLAP = 40


def book_midpoint(gray: Image.Image) -> int:
    """Midpoint between the book's left and right edges."""
    w, _ = gray.size
    small = gray.resize((w // 4, 100))
    px = small.load()
    cols = [sum(px[x, y] for y in range(100)) / 100 for x in range(small.width)]
    bg = (sum(cols[:20]) + sum(cols[-20:])) / 40
    inside = [i for i, c in enumerate(cols) if c > bg + 25]
    if not inside:
        return w // 2
    return (inside[0] + inside[-1]) * 2


def find_gutter(img: Image.Image) -> int:
    gray = ImageOps.grayscale(img)
    w, h = gray.size
    mid = book_midpoint(gray)
    x0, x1 = max(0, mid - int(w * 0.03)), min(w, mid + int(w * 0.03))
    y0, y1 = int(h * 0.2), int(h * 0.8)
    band = gray.crop((x0, y0, x1, y1)).resize((x1 - x0, 50))
    px = band.load()
    cols = [sum(px[x, y] for y in range(50)) for x in range(x1 - x0)]
    # Smooth to ignore single dark strokes of text.
    k = 9
    smooth = [sum(cols[max(0, i - k):i + k + 1]) / len(cols[max(0, i - k):i + k + 1]) for i in range(len(cols))]
    return x0 + min(range(len(smooth)), key=smooth.__getitem__)


def split(path: Path, out_dir: Path) -> None:
    img = Image.open(path)
    img.load()
    w, h = img.size
    g = find_gutter(img)
    right = img.crop((max(0, g - OVERLAP), 0, w, h))
    left = img.crop((0, 0, min(w, g + OVERLAP), h))
    out_dir.mkdir(parents=True, exist_ok=True)
    right.save(out_dir / f"{path.stem}_R.jpg", quality=95)
    left.save(out_dir / f"{path.stem}_L.jpg", quality=95)
    print(f"{path.name}: gutter at x={g} of {w}")


if __name__ == "__main__":
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    out = Path(sys.argv[1])
    for p in sys.argv[2:]:
        split(Path(p), out)
