# Picture Tales of the Myriad Countries (童絵解万国噺, 1861): kuzushiji OCR and English translation

**Read the translation:** https://mrsaturn1.github.io/myriad-countries-kuzushiji-ocr/

In 1861, seven years after Perry's ships opened Japan, the popular writer
**Kanagaki Robun** (仮名垣魯文) and the print artist **Utagawa Yoshitora**
(一孟斎芳虎) published *Osana etoki bankoku banashi*, a picture book telling
children "and women" about the foreign countries now arriving at Japan's ports.
It starts as geography and history (Europe, Peter the Great, the American
colonies and their independence) and turns into a historical romance in which
George Washington slays a mountain monster, and Adams kills a thousand-year-old
serpent with the help of a mountain immortal and a white eagle.

This repository contains:

- a complete **English translation** of Parts 1–4 (about 29,000 words), with an
  introduction, glossary and translator's notes;
- a corrected **Japanese transcription** of every page, from the woodblock-printed
  cursive kana (kuzushiji / hentaigana);
- the **OCR pipeline** used to make that transcription, which can be reused for
  other Edo-period printed books;
- the evaluation that chose the pipeline.

The book itself is public domain. The scans shown are the National Diet
Library's public-domain copy.

## How it was made, and how far to trust it

| Stage | Tool | Accuracy |
|---|---|---|
| OCR, characters | [NDL古典籍OCR-Lite](https://github.com/ndl-lab/ndlkotenocr-lite) (CPU) | 0.95 char F |
| OCR, reading order | [NDL古典籍OCR ver.3](https://github.com/ndl-lab/ndlkotenocr_cli) (GPU, rented on RunPod, about $0.09 in total) | 0.92 char F |
| Merge | `scripts/merge_ocr.py`: Lite's characters in ver.3's reading order, both readings kept where they differ | – |
| Correction | Claude (Anthropic's model) checking every disagreement against enlarged crops of the scan, using a second library's copy for worn spots | **0.98 char F**, 0.96 bigram F |
| Translation | Claude, following `translation/STYLE.md` and a shared glossary | not scored |

Accuracy was measured on five test spreads against careful reference
transcriptions (`ocr/EVALUATION.md`). For comparison, Claude reading the
images with no OCR scored 0.67. The scores are order-insensitive character
and bigram F-measures (`scripts/score_ocr.py`).

Please keep in mind:

- **The translation was made by an AI model and has not been reviewed by a
  specialist** in Edo Japanese. It reads well and the glossary keeps names
  consistent, but expect mistakes.
- Uncertain readings are marked **[?]** (76 of them) and text unreadable in every
  copy is marked **[…]** (19). Robun's history is often wrong or invented; it is
  translated as written, with 83 short translator's notes where a reader might
  be puzzled.
- The 98% figure comes from five spreads. The rest of the book went through the
  same process but was not scored.
- Part 4 ends "to be continued". Robun promised a Part 5, which is not in these
  copies.

Corrections from readers of kuzushiji are very welcome: open an issue or a pull
request against `ocr/final/` or `translation/`.

## What's here

```
docs/                     the reading page (GitHub Pages): each spread's scan beside its English
translation/
  Picture_Tales_of_the_Myriad_Countries.md   the whole book in one file
  intro.md, part1–4.md, appendix.md, glossary.md   its sections (scripts/build_book.py joins them)
  STYLE.md                the translators' style guide
ocr/
  final/                  corrected transcription of each spread (the source for the translation)
  merged/                 Lite + ver.3 merged drafts the correction pass worked from
  ndl_lite_ndlcopy/       NDL OCR Lite output for the NDL copy (text, coordinates)
  ndl_v3/                 NDL OCR ver.3 output for the NDL copy
  CORRECTION_PASS.md      the instructions each correction agent followed
  batches/                the job lists handed to those agents
  EVALUATION.md, reference/, claude/, lightpass/   the OCR comparison and its data
  jobs.tsv, page_plan.tsv, copy_map.tsv            which scan each page was read from
scripts/                  the pipeline (below)
tools/ndlkotenocr-lite/   NDL古典籍OCR-Lite (git submodule)
童絵解万国噺 (1861) - NDL 207-1695/              source notes and IIIF manifests (scans not included)
童絵解万国噺 (1861) - Waseda 文庫11 a0380/       source notes (scans not included)
童絵解万国噺 二編 (1861) - Osaka Pref Lib 乙-342/  source notes and IIIF manifests (scans not included)
```

Transcription format (`ocr/final/*.txt`): one printed column per line, right
page (`## R`) before left (`## L`); lines tagged `[margin]`, `[caption]` or
`[main]`; furigana as 漢字《かな》; `〔字?〕` = uncertain, `■` = unreadable;
then the block order across the spread and a short English note.

## Sources

- **National Diet Library, Tokyo, 207-1695**: the complete four parts in their
  original bindings. NDL Digital Collections
  [2559375](https://dl.ndl.go.jp/pid/2559375),
  [2559376](https://dl.ndl.go.jp/pid/2559376),
  [2559377](https://dl.ndl.go.jp/pid/2559377),
  [2559378](https://dl.ndl.go.jp/pid/2559378). Public domain. This is the main text.
- **Waseda University Library, 文庫11 a0380**
  ([早稲田大学図書館古典籍総合データベース](https://www.wul.waseda.ac.jp/kotenseki/html/bunko11/bunko11_a0380/index.html)):
  a later issue in two volumes. Used for one leaf the NDL copy lacks (Columbus's
  landfall), the endpaper and colophon, and worn spots. Waseda does not allow its
  images to be reposted without permission, so they are not in this repository,
  and the reading page links to them on Waseda's site. Raw OCR output for the
  Waseda copy is omitted for the same reason.
- **Osaka Prefectural Nakanoshima Library, 乙-342**
  ([おおさかeコレクション](https://da.library.pref.osaka.jp/content/detail/01-0007771)):
  a separate copy of Part 2, consulted for its worn passages.

## Reusing the pipeline for another book

The pipeline suits woodblock-printed Edo books (kusazōshi, gōkan, kibyōshi
and similar) scanned as two-page spreads. The scripts need Python 3.10+ with Pillow
and `markdown` (`pip install -r requirements.txt`). Run them from the
repository root with `python3 -I`.

1. **Get scans.** `scripts/download_iiif.py MANIFEST_URL OUT_DIR` downloads every
   page of any IIIF manifest (NDL, Kyoto RMDA, many other libraries) as
   `p0001.jpg`, `p0002.jpg`… Use the highest resolution available; Lite's
   accuracy depends on it.
2. **OCR with NDL古典籍OCR-Lite** (runs on a laptop CPU):
   It is included as a git submodule, pinned to the version used here (`ede4283`,
   July 2026). Clone with `git clone --recursive`, or run the setup script, which
   fetches it and builds a virtualenv in `tools/venv`:
   ```
   sh scripts/setup_tools.sh
   cd tools/ndlkotenocr-lite/src
   ../../venv/bin/python ocr.py --sourcedir "<scan folder>/vol1" --output <out folder>/vol1
   ```
   `scripts/clean_ndl.py` removes lines where it has read illustration hatching
   as text.
3. **OCR with NDL古典籍OCR ver.3** for reading order. It needs an NVIDIA GPU with
   CUDA 12.1. `scripts/runpod_ndl_v3.py up | setup | run | down` rents a
   small RunPod GPU (an RTX A4000 at about $0.17/hour here), installs ver.3, OCRs the scans and terminates
   the pod. Put your RunPod API key in `~/.config/runpod/api_key` or point
   `RUNPOD_KEY_FILE` at it. Edit `SCANS`, `NDL_MANIFESTS` and `WASEDA_BASE` at the
   top for your book. The pod downloads the scans itself rather than having them
   uploaded. Always finish with `down`.
4. **Merge.** `scripts/merge_ocr.py LITE.json V3.json OUT.tsv` pairs each ver.3
   line with the Lite line whose box overlaps it most, and keeps both readings
   where they differ.
5. **Correct.** Give a vision-capable model (we used Claude, through Claude Code
   subagents, one batch of about four spreads each) `ocr/CORRECTION_PASS.md`, a
   scan and its merged draft. Rewrite the "Known traits of this book" section for
   your book. If a second library's copy exists, `scripts/match_copies.py` and
   `scripts/page_plan.py` show how this project matched the two copies' pages
   and picked which to read each page from. Those two scripts are specific to
   this book's copies.
6. **Evaluate** before trusting it. Make careful reference transcriptions of a
   few spreads and score each method with `scripts/score_ocr.py`
   (`scripts/eval_all.py` is this project's harness).
7. **Translate and publish.** `translation/STYLE.md` is the brief the translators
   worked from. `scripts/build_book.py` joins the parts into one Markdown file,
   and `scripts/build_site.py` builds the reading page in `docs/`.

Other useful pieces:

- `scripts/split_pages.py` cuts a spread into right and left pages at the
  binding. It finds the book's edges first, so off-centre photos and dark
  illustrations near the fold don't fool it.
- Lite reads characters better and ver.3 orders them better. Neither copes
  with the ▲/△ marks these books use to continue text in another block of the
  page, so the correction pass fixes block order by hand.

## Licence

- Code (`scripts/`, `docs/index.html`): [MIT](LICENSE).
- Translation, transcriptions and documentation: [CC BY 4.0](LICENSE-CONTENT.md).
- The 1861 book is in the public domain. The scans in `docs/scans/` are
  downscaled copies of the National Diet Library's public-domain images
  (credit: 国立国会図書館デジタルコレクション).
- NDL古典籍OCR-Lite and ver.3 are by the National Diet Library (CC BY 4.0).
  Lite is linked as a submodule in `tools/ndlkotenocr-lite`; ver.3 is installed
  on the GPU pod by `scripts/runpod_ndl_v3.py`.
