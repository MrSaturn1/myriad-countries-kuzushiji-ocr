# OCR evaluation (2026-10-08)

Five sample spreads (Waseda vol1 p0005, p0009, p0020; vol2 p0014, p0029), chosen
to range from a short preface to the densest text in the book.

## Reference
`ocr/reference/` — one agent per spread built a careful transcription from both
library scans (mainly the sharper NDL copy), adjudicating every disagreement
between the candidates against enlarged crops. Self-rated 92–96% certain.
Caveat: the reference makers could see the candidates, so the reference may lean
slightly toward the OCR tools' readings.

## Score
`scripts/eval_all.py` (uses `scripts/score_ocr.py`). Furigana is dropped; scores
ignore reading order (the tools order lines very differently):
- **char F**: overlap of characters (1.00 = perfect)
- **bigram F**: overlap of adjacent character pairs — rewards correct runs of text

## Results (weighted by reference length)

| Method | char F | bigram F |
|---|---|---|
| **Correction pass** (Lite + v3 merged, checked against the image by Claude Opus 5.5) | **0.98** | **0.96** |
| NDL古典籍OCR-Lite on NDL copy (~4500 px) | 0.95 | 0.91 |
| NDL古典籍OCR-Lite on Waseda copy (2592 px) | 0.95 | 0.90 |
| NDL古典籍OCR ver.3 on Waseda copy | 0.92 | 0.84 |
| NDL古典籍OCR ver.3 on NDL copy | 0.92 | 0.84 |
| Claude Opus 5.5 reading the image alone | 0.67 | 0.33 |

## Findings
- **Lite reads characters best**; ver.3 (the "full" GPU version, run on RunPod)
  is ~3 points behind on characters but produces clean, mostly correct reading
  order without illustration noise or interleaved furigana.
- ver.3's block order breaks where the text continues via ▲/△ marks.
- Claude alone cannot reliably read dense hentaigana at this resolution, but is
  good at adjudicating between OCR readings with the image and context.
- The correction pass also fixes what these scores don't measure: block order,
  captions, page numbers and running titles, furigana on names, worn spots
  (read from the other library's scan).
- miwo was not tested (phone-only; skipped).

## Pipeline used for the whole book
1. `scripts/page_plan.py` — NDL copy as primary; Waseda half-pages missing from
   it added → `ocr/jobs.tsv` (92 jobs).
2. `scripts/merge_ocr.py` — Lite text in ver.3 order, both readings per line → `ocr/merged/`.
3. Correction pass per `ocr/CORRECTION_PASS.md` → `ocr/final/` (the four sample
   spreads with NDL counterparts reuse their references).
4. Translation → `translation/`.
