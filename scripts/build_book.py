"""Assemble the full English translation into one Markdown file.

Concatenates translation/intro.md, part1–4.md, appendix.md and glossary.md
(in that order) into translation/Picture_Tales_of_the_Myriad_Countries.md,
with a table of contents built from the Part headings.

Usage:  python3 -I scripts/build_book.py
"""
import re
from pathlib import Path

T = Path(__file__).resolve().parent.parent / "translation"
SECTIONS = ["intro.md", "part1.md", "part2.md", "part3.md", "part4.md", "appendix.md", "glossary.md"]
OUT = T / "Picture_Tales_of_the_Myriad_Countries.md"

bodies = []
for name in SECTIONS:
    text = (T / name).read_text(encoding="utf-8").strip()
    if name == "glossary.md":
        # The glossary's own title becomes an appendix heading.
        text = re.sub(r"^# .*", "# Glossary of names and terms", text, count=1)
    bodies.append(text)

toc = ["## Contents", ""]
for body in bodies[1:]:
    m = re.search(r"^# (.+)$", body, flags=re.M)
    if m:
        title = m.group(1).strip()
        anchor = re.sub(r"[^\w\- ]", "", title.lower()).replace(" ", "-")
        toc.append(f"- [{title}](#{anchor})")

intro = bodies[0]
book = intro + "\n\n" + "\n".join(toc) + "\n\n---\n\n" + "\n\n---\n\n".join(bodies[1:]) + "\n"
OUT.write_text(book, encoding="utf-8")
words = len(re.findall(r"[A-Za-z']+", book))
print(f"{OUT.name}: {words:,} words, {sum(b.count(chr(10) + '### ') for b in bodies)} spread sections")
