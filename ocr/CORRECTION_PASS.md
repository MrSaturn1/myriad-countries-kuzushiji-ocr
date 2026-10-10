# Correction pass: merged OCR draft → clean transcription

You are producing a clean Japanese transcription of one two-page spread from the
public-domain 1861 woodblock-printed children's book 童絵解万国噺 (仮名垣魯文 作,
歌川芳虎 画), about foreign countries and the founding of America.

Root folder: the project root (paths below are relative to it).

## Inputs (given per spread in your task)
- **SCAN**: the spread image the OCR ran on. Right page is read first.
- **DRAFT**: `ocr/merged/.../pNNNN.tsv`, one row per detected text line:
  `n  status  x0 y0 x1 y1  lite_text  v3_text` — coordinates are pixels in SCAN.
  - Rows are in NDL OCR ver.3's reading order (usually right, but its BLOCK order
    can be wrong where text continues via ▲/△/○ marks or つゞき/つゞく boxes).
  - `lite_text` (NDL OCR Lite) is the more accurate reader: ~95% of characters right.
    `v3_text` is a second opinion.
  - status `same`: both agree → accept unless it is clearly wrong in context.
  - `diff`: they disagree → crop that box from SCAN, upscale 3×, decide. Often
    one reading is right; sometimes neither.
  - `v3only` / `liteonly`: only one tool saw it → check the crop; it may be real
    text (caption, label, furigana, page number) or noise from the illustration.
  - `noise`: almost always hatching misread as text; glance, then drop.
- **ALT_SCAN** (optional): another library's scan of the same spread, for
  worn or creased spots.

## Method
1. Look at the whole SCAN once (downscaled) to see the layout: text blocks,
   captions, the ▲/△/○ continuation marks, つゞき/つゞく boxes, margins.
2. Work through DRAFT rows. Crop with Pillow from the venv:
   `"<root>/tools/venv/bin/python" -I` (heredoc). Pad boxes ~20 px. Keep crops
   and scratch scripts in `ocr/work/<SPREAD_ID>/` — never a shared directory.
3. Resolve `diff` rows; check `v3only`/`liteonly` rows; skim `same` rows in
   context (both tools can share an error — known shared ones below).
4. Fix BLOCK order using the continuation marks, not the draft's order.
5. Look for text no row covers (small captions, labels, margin page numbers).
6. Furigana: include it (漢字《かな》) for names, foreign words, and unusual
   readings; skip routine readings of common kanji. Don't spend long on it.

## Known traits of this book and these tools
- こ is often written in a hentaigana form that looks like と.
- ことごとく is printed こと + a く-shaped repeat mark → write こと〴〵く.
- Both tools drop dakuten the print has and add ones it lacks; follow the print.
- Both tools write 一つ for printed 一ツ, and often drop 〳〵.
- Lite modernises some kanji (國→国); keep the form actually printed.
- い is often written in a form that looks like ら (いたりや "Italy" came out
  as らたりや); check い/ら in names especially.
- Closing boxes read つゞく or つぎへ; opening boxes つゞき or 〇の巻より.
- Foreign names are in kana: めりけん, はりな, わしんとん, ふらんくりん, あゝだむす,
  ころんぶす, ごるとん, めれしこう … Read them carefully; they matter for translation.
- The 柱 (running title, e.g. 万国初 / 万国二) and page numbers sit in the outer
  margins and are often half cut by the binding; record what is visible.
- Some spreads are title pages, prefaces, a publisher's catalogue, a colophon or
  full-page pictures with only labels — transcribe whatever text there is.

## Jobs that cover only one half
If your job says `pages: R` or `pages: L`, transcribe only that page (the other
half is covered by another job or isn't part of the book); still write `## R`
or `## L` as appropriate and omit the other.

## Output: `ocr/final/<SPREAD_ID>.txt`, UTF-8
```
## R
[margin] <柱 / page number>
[caption] <caption or label>
[main] <main text, one printed column per line, in reading order>
## L
...
## order
<one line: the block order across the spread, e.g. "R top → L top ▲ → R bottom ▲ → L bottom つゞく">
## notes
<1–2 sentence English summary; any spots you were unsure of>
```
- Kana → standard modern kana; kanji as printed; 〳〵 ゝ ゞ as printed;
  no added dakuten.
- ■ = unreadable, 〔字?〕 = unsure. Don't invent text for fluency.
- Do not search the web for transcriptions of this book.

Reply with: output path, character count, number of ■ and 〔?〕.
