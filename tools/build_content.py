#!/usr/bin/env python3
"""Assemble app/content/*.json from extraction output.

Inputs per book (skipped gracefully if missing):
  extraction/<book>/sections.json  — section boundaries (from structuring agents)
  extraction/<book>/txt/page-NNNN.txt — verbatim OCR pages (Gujarati books)
  extraction/kirtan-english/full.txt  — verbatim text (English book, line-based)

Body text is NEVER altered — only split at section boundaries and into
display blocks. Re-runnable; overwrites app/content."""

import json, re, sys
from pathlib import Path

BASE = Path("/Users/harsh/RamKabir")
EXT = BASE / "extraction"
OUT = BASE / "app" / "content"
OUT.mkdir(parents=True, exist_ok=True)

BOOKS = [
    dict(id="samagam-purvardh",  title_gu="સમાગમ (પૂર્વાર્ધ)",  title_en="Samagam — Purvardh",  language="gu"),
    dict(id="samagam-uttarardh", title_gu="સમાગમ (ઉત્તરાર્ધ)", title_en="Samagam — Uttarardh", language="gu"),
    dict(id="kirtan-gujarati",   title_gu="શ્રી અધ્યારુજીનાં કીર્તન", title_en="Shree Padmanabhji Adhyaruji na Kirtan", language="gu",
         idx_range=(1, 38)),
    dict(id="jivandas-sakhi",    title_gu="વૈષ્ણવ જીવણદાસજીકી સાખી", title_en="Vaishnav Jivandasji ki Sakhi", language="gu",
         src="kirtan-gujarati", idx_range=(39, 64)),
    dict(id="kirtan-english",    title_gu="અધ્યારુજીનાં કીર્તન (English)", title_en="Adhyaruji na Kirtan — English transliteration", language="translit"),
    dict(id="sant-darshan",      title_gu="સંત દર્શન",           title_en="Sant Darshan",        language="gu"),
]

# Leading sections to collapse into one "front matter" TOC entry, per book.
# (Purvardh: cover + 6 front-matter sections, several of which are the Kirtan
# volume's pages mistakenly bound into the scan.)
FRONT_MATTER_SECTIONS = {"samagam-purvardh": 7, "sant-darshan": 4}
FRONT_MATTER_TITLE = "પ્રારંભિક પાનાં"

# Pinned quick-access items on the library home screen (Harsh's request:
# the Vani "Parabrahma vani re…" is in frequent use). Resolved by exact
# section-title match at build time so indices never go stale.
FEATURED = [
    {"book": "kirtan-gujarati", "title": "વાણી", "label_gu": "વાણી", "label_en": "Parabrahma vani re…"},
    {"book": "kirtan-english",  "title": "Vani", "label_gu": "Vani (English)", "label_en": "Parbrahm vani re parni e…"},
]

def page_text(book_id, n):
    # image-grounded corrected pages (txt-corrected/) win over raw OCR
    for sub in ("txt-corrected", "txt"):
        p = EXT / book_id / sub / f"page-{n:04d}.txt"
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
    return ""

def build_gujarati(book):
    src = book.get("src", book["id"])
    sec_file = EXT / src / "sections.json"
    txt_dir = EXT / src / "txt"
    if not sec_file.exists() or not txt_dir.exists():
        return None
    spec = json.loads(sec_file.read_text(encoding="utf-8"))
    n_pages = len(list(txt_dir.glob("page-*.txt")))
    specs = spec["sections"]
    if "idx_range" in book:
        lo, hi = book["idx_range"]
        specs = [s for s in specs if lo <= s["idx"] <= hi]
    n_front = FRONT_MATTER_SECTIONS.get(book["id"], 0)
    if n_front > 1:
        front, rest = specs[:n_front], specs[n_front:]
        merged = dict(front[0], title_gu=FRONT_MATTER_TITLE,
                      end_page=front[-1]["end_page"])
        specs = [merged] + rest
    if "idx_range" in book and specs:
        n_pages = specs[-1]["end_page"] - specs[0]["start_page"] + 1
    sections = []
    for s in specs:
        blocks = []
        for pg in range(s["start_page"], s["end_page"] + 1):
            t = page_text(src, pg).strip()
            if t:
                blocks.append({"page": pg, "text": t})
        title = s.get("title_gu") or s.get("title") or f"વિભાગ {s['idx']}"
        sections.append({"title": title.strip(), "page_start": s["start_page"], "blocks": blocks})
    return dict(book, pages=n_pages, sections=sections)

def build_english(book):
    sec_file = EXT / "kirtan-english" / "sections.json"
    full = EXT / "kirtan-english" / "full.txt"
    if not sec_file.exists() or not full.exists():
        return None
    lines = full.read_text(encoding="utf-8", errors="replace").splitlines()
    spec = json.loads(sec_file.read_text(encoding="utf-8"))
    sections = []
    for s in spec["sections"]:
        seg = lines[s["start_line"] - 1 : s["end_line"]]
        # split into blocks on blank lines; track "(N)" page markers
        blocks, cur, cur_page = [], [], None
        def flush():
            nonlocal cur
            t = "\n".join(cur).rstrip()
            # collapse the pdftotext column padding: runs of 3+ spaces -> single space
            t = re.sub(r" {3,}", "  ", t)
            if t.strip():
                blocks.append({"page": cur_page, "text": t})
            cur = []
        for ln in seg:
            m = re.fullmatch(r"\s*\((\d+)\)\s*", ln)
            if m:
                flush()
                cur_page = int(m.group(1))
                continue
            if not ln.strip():
                if len(cur) > 12:
                    flush()
                else:
                    cur.append("")
                continue
            cur.append(ln)
        flush()
        sections.append({"title": s["title"].strip(), "page_start": None, "blocks": blocks})
    return dict(book, pages=143, sections=sections)

manifest = []
for book in BOOKS:
    built = build_english(book) if book["id"] == "kirtan-english" else build_gujarati(book)
    if built is None:
        print(f"skip {book['id']} (no sections.json / txt yet)")
        continue
    (OUT / f"{book['id']}.json").write_text(
        json.dumps(built, ensure_ascii=False), encoding="utf-8")
    manifest.append({k: built[k] for k in ("id", "title_gu", "title_en", "language", "pages")}
                    | {"sections_count": len(built["sections"])})
    print(f"built {book['id']}: {len(built['sections'])} sections, "
          f"{sum(len(s['blocks']) for s in built['sections'])} blocks")

featured = []
for f in FEATURED:
    built_file = OUT / f"{f['book']}.json"
    if not built_file.exists():
        continue
    secs = json.loads(built_file.read_text(encoding="utf-8"))["sections"]
    hits = [i for i, s in enumerate(secs) if s["title"].strip() == f["title"]]
    if len(hits) == 1:
        featured.append({"book": f["book"], "section": hits[0],
                         "label_gu": f["label_gu"], "label_en": f["label_en"]})
        print(f"featured: {f['label_gu']} -> {f['book']}#{hits[0]}")
    else:
        print(f"featured UNRESOLVED ({len(hits)} matches): {f['title']} in {f['book']}")

(OUT / "books.json").write_text(
    json.dumps({"books": manifest, "featured": featured}, ensure_ascii=False, indent=1),
    encoding="utf-8")
print(f"manifest: {len(manifest)} books, {len(featured)} featured")
