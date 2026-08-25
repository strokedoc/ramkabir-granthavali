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
WARNINGS = []  # fail-loud: split-needle misses abort the build

BOOKS = [
    dict(id="samagam-purvardh",  title_gu="સમાગમ (પૂર્વાર્ધ)",  title_en="Samagam — Purvardh",  language="gu"),
    dict(id="samagam-uttarardh", title_gu="સમાગમ (ઉત્તરાર્ધ)", title_en="Samagam — Uttarardh", language="gu"),
    dict(id="kirtan-gujarati",   title_gu="શ્રી અધ્યારુજીનાં કીર્તન", title_en="Shree Padmanabhji Adhyaruji na Kirtan", language="gu",
         idx_range=(1, 38)),
    dict(id="jivandas-sakhi",    title_gu="વૈષ્ણવ જીવણદાસજીકી સાખી", title_en="Vaishnav Jivandasji ki Sakhi", language="gu",
         src="kirtan-gujarati", idx_range=(39, 64)),
    dict(id="kirtan-english",    title_gu="અધ્યારુજીનાં કીર્તન (અંગ્રેજી)", title_en="Adhyaruji na Kirtan — English transliteration", language="translit"),
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
    {"book": "kirtan-gujarati", "title": "વાણી", "label_gu": "વાણી", "label_en": "Vani — Parabrahma vani re…"},
    {"book": "kirtan-english",  "title": "Vani", "label_gu": "વાણી (અંગ્રેજી)", "label_en": "Vani (English) — Parbrahm vani re…"},
]

def page_text(book_id, n):
    # image-grounded corrected pages (txt-corrected/) win over raw OCR
    for sub in ("txt-corrected", "txt"):
        p = EXT / book_id / sub / f"page-{n:04d}.txt"
        if p.exists():
            return p.read_text(encoding="utf-8", errors="replace")
    return ""

def load_splits(src):
    """extraction/<src>/splits.json — sub-page section starts.
    {"<page>": {"before": <heading line>} | {"after": <prev's last line>},
     optional "replace": <clean heading>}. Needles are matched fuzzily
    (letters only) against the page's lines."""
    p = EXT / src / "splits.json"
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else {}

def _norm_line(s):
    # NB: strip dandas (। ॥ live inside the Devanagari block) so single- vs
    # double-danda variants of the same heading still match
    return re.sub(r"[।॥]", "", re.sub(r"[^઀-૿ऀ-ॿA-Za-z]", "", s))

def split_page(text, sp):
    """Return (head, tail) of a page's text per its split spec; (None, None) if
    the needle can't be found (caller falls back to unsplit)."""
    lines = text.split("\n")
    mode = "before" if "before" in sp else "after"
    def find(needle):
        if not needle:
            return None
        k = next((i for i, ln in enumerate(lines) if _norm_line(ln) == needle), None)
        if k is None:
            k = next((i for i, ln in enumerate(lines)
                      if needle in _norm_line(ln) or
                         (len(_norm_line(ln)) >= 6 and _norm_line(ln) in needle)), None)
        return k
    k = find(_norm_line(sp[mode]))
    if k is None and "replace" in sp:
        # the repair pass may have replaced the garbled needle line with clean
        # text — which is exactly what "replace" holds; match on that instead
        k = find(_norm_line(sp["replace"].split("\n")[0]))
    if k is None:
        return None, None
    cut = k if mode == "before" else k + 1
    head = "\n".join(lines[:cut]).rstrip()
    tail_lines = lines[cut:]
    extras = [_norm_line(x) for x in sp.get("extra_heading_lines", [])]
    if extras:
        tail_lines = [ln for ln in tail_lines if _norm_line(ln) not in extras]
    head, tail = head, "\n".join(tail_lines).strip()
    if "replace" in sp and tail:
        if mode == "before":
            tl = tail.split("\n")
            tl[0] = sp["replace"]
            tail = "\n".join(tl)
        else:
            tail = sp["replace"] + "\n" + tail
    return head, tail

def build_gujarati(book):
    src = book.get("src", book["id"])
    sec_file = EXT / src / "sections.json"
    txt_dir = EXT / src / "txt"
    if not sec_file.exists() or not txt_dir.exists():
        return None
    splits = load_splits(src)
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
    # a page may carry 1..n split points (n+1 parts); part 0 belongs to the
    # section arriving from the previous page, part i to the i-th section
    # that STARTS on the page (in spec order)
    def page_parts(pg):
        sp = splits.get(str(pg))
        if not sp:
            return None
        sps = sp if isinstance(sp, list) else [sp]
        rest = page_text(src, pg).strip()
        parts = []
        for one in sps:
            head, tail = split_page(rest, one)
            if head is None:
                print(f"  ! split needle not found on p{pg} ({book['id']})")
                WARNINGS.append(f"{book['id']} p{pg}")
                return None
            parts.append(head)
            rest = tail
        parts.append(rest)
        return parts

    starters = {}  # page -> ordered spec indices starting there
    for i, s in enumerate(specs):
        starters.setdefault(s["start_page"], []).append(i)

    def n_splits(pg):
        sp = splits.get(str(pg))
        return 0 if sp is None else (len(sp) if isinstance(sp, list) else 1)

    sections = []
    for si, s in enumerate(specs):
        blocks = []
        for pg in range(s["start_page"], s["end_page"] + 1):
            parts = page_parts(pg)
            if parts is None:
                t = page_text(src, pg).strip()
            elif pg == s["start_page"]:
                # k splits, m starters: k==m → part 0 belongs to the section
                # arriving from the previous page; k==m-1 → the first starter
                # opens the page top, so starter i takes part i
                m = len(starters[pg])
                off = 1 if len(parts) - 1 == m else 0
                t = parts[off + starters[pg].index(si)]
            else:
                t = parts[0]
            # skip blocks that are pure punctuation/frame artifacts or a bare folio
            if t and _norm_line(t):
                blocks.append({"page": pg, "text": t})
        # spill-over: a section starts mid-page on the page after ours —
        # that page's part 0 belongs to us (only when no starter owns the top)
        nxt = s["end_page"] + 1
        if str(nxt) in splits and n_splits(nxt) == len(starters.get(nxt, [])) and \
           (si + 1 == len(specs) or specs[si + 1]["start_page"] == nxt):
            parts = page_parts(nxt)
            if parts and _norm_line(parts[0]):
                blocks.append({"page": nxt, "text": parts[0].strip()})
        title = s.get("title_gu") or s.get("title") or f"વિભાગ {s['idx']}"
        sections.append({"title": title.strip(), "page_start": s["start_page"], "blocks": blocks})
    # inline sub-headings (extraction/<src>/subheads.json: {"<page>": [lines]}):
    # split blocks so each sub-heading becomes its own block with sub:true
    sh_file = EXT / src / "subheads.json"
    if sh_file.exists():
        subheads = json.loads(sh_file.read_text(encoding="utf-8"))
        for sec in sections:
            out = []
            for bl in sec["blocks"]:
                heads = [_norm_line(h) for h in subheads.get(str(bl["page"]), [])]
                if not heads:
                    out.append(bl)
                    continue
                cur = []
                for ln in bl["text"].split("\n"):
                    if _norm_line(ln) in heads:
                        if cur and any(_norm_line(x) for x in cur):
                            out.append({"page": bl["page"], "text": "\n".join(cur).strip()})
                        out.append({"page": bl["page"], "text": ln.strip(), "sub": True})
                        cur = []
                    else:
                        cur.append(ln)
                if cur and any(_norm_line(x) for x in cur):
                    out.append({"page": bl["page"], "text": "\n".join(cur).strip()})
            sec["blocks"] = out
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
if WARNINGS:
    print(f"BUILD FAILED — unresolved split needles: {WARNINGS}")
    sys.exit(1)
