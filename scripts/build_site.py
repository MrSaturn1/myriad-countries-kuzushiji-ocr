"""Build the reading web page for the English translation.

Writes docs/index.html plus docs/scans/<job>.jpg (downscaled copies of each
spread), ready for GitHub Pages. Every spread section shows its scan beside
the English, with the corrected Japanese transcription from ocr/final/ in
vertical type underneath.

Only public-domain NDL scans are copied. Waseda University Library does not
allow its images to be reposted without permission (linking is allowed), so
spreads read from the Waseda copy link to the image on Waseda's site instead;
where the NDL copy has the same picture, that scan is shown.

Usage:  python3 -I scripts/build_site.py
"""
import html
import re
from pathlib import Path

import markdown
from PIL import Image

ROOT = Path(__file__).resolve().parent.parent
T = ROOT / "translation"
FINAL = ROOT / "ocr" / "final"
OUT = ROOT / "docs"
SCANS = OUT / "scans"
PARTS = ["part1.md", "part2.md", "part3.md", "part4.md", "appendix.md"]
SCAN_WIDTH = 1800
REPO = "https://github.com/MrSaturn1/myriad-countries-kuzushiji-ocr"
WASEDA_URL = "https://archive.wul.waseda.ac.jp/kosho/bunko11/bunko11_a0380/bunko11_a0380_000{n}/bunko11_a0380_000{n}_{page}.jpg"

HEAD_RE = re.compile(r"^### (.+?) — (\S+)\s+\(scan: (.+?\.jpg)(.*)\)\s*$")


def md(text):
    """Markdown → HTML, with translator's notes and uncertainty marks styled."""
    text = mark_notes(text)
    out = markdown.markdown(text, extensions=["tables", "sane_lists"])
    out = re.sub(r'<p><span class="tn">(.*?)</span></p>', r'<p class="tn">\1</p>', out, flags=re.S)
    out = out.replace("[?]", '<sup class="q" title="Uncertain reading">?</sup>')
    out = out.replace("[…]", '<span class="gap" title="Unreadable in every copy">[…]</span>')
    out = out.replace("<table>", '<div class="tablewrap"><table>').replace("</table>", "</table></div>")
    return out


def mark_notes(text):
    """Wrap each [T.N. …] (brackets may nest) in a span."""
    out, i = [], 0
    while (j := text.find("[T.N.", i)) != -1:
        out.append(text[i:j])
        depth, k = 0, j
        while k < len(text):
            depth += {"[": 1, "]": -1}.get(text[k], 0)
            if depth == 0:
                break
            k += 1
        body = text[j + 5:k].strip()
        out.append(f'<span class="tn"><b>Translator\'s note.</b> {body}</span>')
        i = k + 1
    out.append(text[i:])
    return "".join(out)


def japanese(job):
    """Render ocr/final/<job>.txt as vertical columns, right page first."""
    path = FINAL / f"{job}.txt"
    if not path.exists():
        return ""
    pages, cur, block = [], None, None
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.startswith("## "):
            name = line[3:].strip()
            cur = {"name": name, "blocks": []} if name in ("R", "L") else None
            if cur:
                pages.append(cur)
            block = None
            continue
        if cur is None or not line.strip() or line.startswith("[margin]"):
            continue
        if line.startswith("[caption]"):
            cur["blocks"].append(("cap", [line[9:].strip()]))
            block = None
        elif line.startswith("[main]"):
            block = ("main", [line[6:].strip()])
            cur["blocks"].append(block)
        else:
            if block is None:
                block = ("main", [])
                cur["blocks"].append(block)
            block[1].append(line.strip())

    def esc(s):
        s = html.escape(s)
        s = re.sub(r"〔(.+?)\?〕", r'<span class="unc" title="Uncertain reading">\1</span>', s)
        return s.replace("■", '<span class="gapj">■</span>')

    parts = []
    for p in pages:
        label = "Right page" if p["name"] == "R" else "Left page"
        blocks = "".join(
            f'<p class="{kind}">' + "<br>".join(esc(l) for l in lines) + "</p>"
            for kind, lines in p["blocks"] if lines
        )
        parts.append(f'<div class="jpage" aria-label="{label}">{blocks}</div>')
    return "".join(parts)


def scan(job, src):
    dest = SCANS / f"{job}.jpg"
    if not dest.exists():
        im = Image.open(ROOT / src).convert("RGB")
        if im.width > SCAN_WIDTH:
            im = im.resize((SCAN_WIDTH, round(im.height * SCAN_WIDTH / im.width)), Image.LANCZOS)
        im.save(dest, "JPEG", quality=72, optimize=True, progressive=True)
    with Image.open(dest) as im:
        return im.size


def img_figure(job, short, w, hgt, cap):
    return f"""<figure class="scan">
    <button class="zoom" type="button" data-src="scans/{job}.jpg" aria-label="Enlarge scan of {html.escape(short)}">
      <img src="scans/{job}.jpg" width="{w}" height="{hgt}" loading="lazy" decoding="async" alt="Scan of the spread: {html.escape(short)}">
    </button>
    <figcaption>{cap}</figcaption>
  </figure>"""


def source_label(src):
    if "Waseda" in src:
        lib = "Waseda Univ. Library"
    elif "Osaka" in src:
        lib = "Osaka Pref. Library"
    else:
        lib = "National Diet Library"
    m = re.search(r"/(vol\d)/(p\d+)\.jpg", src)
    return f"{lib} · {m[1]} {m[2]}" if m else lib


def build_part(name, idx):
    text = (T / name).read_text(encoding="utf-8")
    title = re.search(r"^# (.+)$", text, re.M)[1]
    pid = "appendix" if name == "appendix.md" else f"part{idx}"
    chunks = re.split(r"^(?=### )", text, flags=re.M)
    pre = re.sub(r"^# .+$", "", chunks[0], count=1, flags=re.M).replace("\n---\n", "\n")
    m = re.match(r"(Part \w+|Appendix)(?: \((.+?)\))?: (.+)", title)
    kicker, jp, sub = (m[1], m[2] or "", m[3]) if m else (title, "", "")
    sections, nav = [], []
    for ch in chunks[1:]:
        head, _, body = ch.partition("\n")
        h = HEAD_RE.match(head)
        label, job, src, extra = h[1], h[2], h[3], h[4].strip("; ").strip()
        short = re.sub(r"^Part \d, ", "", label)
        alt = re.search(r"same picture in NDL (vol\d)/(p\d+)\.jpg", extra)
        if "Waseda" in src and alt:
            ndl_src = f"童絵解万国噺 (1861) - NDL 207-1695/{alt[1]}/{alt[2]}.jpg"
            w, hgt = scan(job, ndl_src)
            cap = source_label(ndl_src) + " · same picture as the Waseda copy, whose text is followed here"
            figure = img_figure(job, short, w, hgt, cap)
        elif "Waseda" in src:
            m = re.search(r"/vol(\d)/(p\d+)\.jpg", src)
            url = WASEDA_URL.format(n=m[1], page=m[2])
            figure = f"""<figure class="scan away">
    <a class="awaybox" href="{url}" target="_blank" rel="noopener">
      <span class="awaykick">Waseda copy only</span>
      <span>This page is not in the National Diet Library copy. Waseda University Library does not allow its images to be reposted, so view the scan on Waseda's site.</span>
      <span class="awaygo">Open the scan ↗</span>
    </a>
    <figcaption>{source_label(src)} · 早稲田大学図書館古典籍総合データベース</figcaption>
  </figure>"""
        else:
            w, hgt = scan(job, src)
            cap = source_label(src) + (f" · {html.escape(extra)}" if extra else "")
            figure = img_figure(job, short, w, hgt, cap)
        ja = japanese(job)
        ja_html = (
            f'<details class="ja"><summary>Japanese transcription</summary>'
            f'<div class="jscroll" lang="ja">{ja}</div></details>' if ja else ""
        )
        sections.append(f"""
<section class="spread" id="{job}">
  {figure}
  <div class="text">
    <h3><span class="where">{html.escape(kicker)}</span> {md(short)[3:-4]}</h3>
    {md(body)}
    {ja_html}
  </div>
</section>""")
        nav.append(f'<li><a href="#{job}">{md(short)[3:-4]}</a></li>')
    head = f"""
<header class="parthead" id="{pid}">
  <p class="kicker">{html.escape(kicker)}{f' <span lang="ja">{html.escape(jp)}</span>' if jp else ''}</p>
  <h2>{html.escape(sub)}</h2>
  <div class="partnote">{md(pre.strip())}</div>
</header>"""
    navhtml = (f'<li class="navpart"><details{" open" if idx == 1 else ""}><summary><a href="#{pid}">'
               f'{html.escape(kicker)}</a><span>{html.escape(sub)}</span></summary><ol>{"".join(nav)}</ol></details></li>')
    return head + "".join(sections), navhtml, pid, kicker, sub


def main():
    SCANS.mkdir(parents=True, exist_ok=True)
    intro = (T / "intro.md").read_text(encoding="utf-8")
    about = intro.split("## About this book", 1)[1]
    # The conventions were written for the Markdown edition; describe this page instead.
    about = about.replace("- **[T.N. …]** is a translator's note.", "- Translator's notes are set in smaller grey type.")
    about = about.replace("The heading names\n  the scan it comes from, so you can look at the picture while you read.",
                          "Its scan sits beside\n  the English; select it to enlarge.")
    intro_html = md("## About this book" + about)
    glossary = (T / "glossary.md").read_text(encoding="utf-8")
    glossary = re.sub(r"^# .*\n", "", glossary, count=1)
    glossary = re.sub(r"Seeded from\s+the transcription pass; translators add new entries under their part\.", "", glossary)
    body, nav, toc = [], [], []
    for i, name in enumerate(PARTS, 1):
        h, n, pid, kicker, sub = build_part(name, i)
        body.append(h)
        nav.append(n)
        toc.append(f'<li><a href="#{pid}"><span class="tockick">{html.escape(kicker)}</span>{html.escape(sub)}</a></li>')
    nav.append('<li class="navpart solo"><a href="#glossary">Glossary</a></li>')
    toc.append('<li><a href="#glossary"><span class="tockick">Glossary</span>Names and terms</a></li>')
    page = (ROOT / "scripts" / "site_template.html").read_text(encoding="utf-8")
    page = (page.replace("{{INTRO}}", intro_html)
                .replace("{{TOC}}", "".join(toc))
                .replace("{{NAV}}", "".join(nav))
                .replace("{{BODY}}", "".join(body))
                .replace("{{GLOSSARY}}", md(glossary))
                .replace("{{REPO}}", REPO))
    (OUT / "index.html").write_text(page, encoding="utf-8")
    size = sum(p.stat().st_size for p in SCANS.glob("*.jpg"))
    print(f"index.html {len(page)/1024:.0f} KB; {len(list(SCANS.glob('*.jpg')))} scans, {size/1e6:.1f} MB")


main()
