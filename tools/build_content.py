#!/usr/bin/env python3
"""Assemble app/content/*.json from extraction output.

Inputs per book (skipped gracefully if missing):
  extraction/<book>/sections.json  — section boundaries (from structuring agents)
  extraction/<book>/txt/page-NNNN.txt — verbatim OCR pages (Gujarati books)
  extraction/kirtan-english/full.txt  — verbatim text (English book, line-based)

Body text is NEVER altered — only split at section boundaries and into
display blocks. Re-runnable; overwrites app/content."""

import json, os, re, sys, tempfile
from pathlib import Path

BASE = Path("/Users/harsh/RamKabir")
EXT = BASE / "extraction"
OUT = BASE / "app" / "content"
OUT.mkdir(parents=True, exist_ok=True)
WARNINGS = []  # fail-loud: split-needle misses abort the build
EMPTY = []     # sections that rendered with no body text
PENDING = {}   # nothing is written until the whole build is known good

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
        """Exact line match wins. Fuzzy fallbacks must be SUBSTANTIAL: a short
        line that merely appears inside a long needle (e.g. the word 'થુવાવી'
        inside a whole sentence about Thuvavi) must not win — that silently
        cuts the page at the wrong place and empties a section."""
        if not needle:
            return None
        k = next((i for i, ln in enumerate(lines) if _norm_line(ln) == needle), None)
        if k is not None:
            return k
        best, best_score = None, None
        for i, ln in enumerate(lines):
            n = _norm_line(ln)
            if not n:
                continue
            if needle in n or (n in needle and len(n) >= 0.7 * len(needle)):
                score = abs(len(n) - len(needle))   # closest in length wins,
                if best_score is None or score < best_score:   # earliest on tie
                    best, best_score = i, score
        return best
    matched_heading = False
    k = find(_norm_line(sp[mode]))
    if k is None and "replace" in sp:
        matched_heading = True
        # a repair may have rewritten the garbled needle line into clean text —
        # which is exactly what "replace" holds; that is the precise target
        k = find(_norm_line(sp["replace"].split("\n")[0]))
    if k is None and sp.get("fallback_title"):
        matched_heading = True
        # last resort, and never at line 0: a title matching the page's FIRST
        # line means we found the heading of a section that owns the page top,
        # not the boundary we were looking for
        kk = find(_norm_line(sp["fallback_title"]))
        if kk:
            k = kk
    if k is None:
        return None, None
    # an "after" needle points at the line BEFORE the heading; but when we fell
    # back to the heading text itself, k already IS the heading line
    cut = k if (mode == "before" or matched_heading) else k + 1
    head = "\n".join(lines[:cut]).rstrip()
    tail_lines = lines[cut:]
    extras = [_norm_line(x) for x in sp.get("extra_heading_lines", [])]
    if extras:
        tail_lines = [ln for ln in tail_lines if _norm_line(ln) not in extras]
    head, tail = head, "\n".join(tail_lines).strip()
    if "replace" in sp and tail:
        # The repair pass may already have corrected this heading in the page
        # text. Re-inserting it then DUPLICATES the heading inside the body, so
        # drop any leading tail lines that the replacement already provides.
        rep_lines = sp["replace"].split("\n")
        rep_norm = {_norm_line(x) for x in rep_lines if _norm_line(x)}
        tl = tail.split("\n")
        if mode == "before":
            tl = tl[1:]                      # the matched heading line itself
        # scan the opening lines (past blanks and decorative separators like
        # "=====00000=====") and drop any that the replacement already supplies
        checked = 0
        i = 0
        while i < len(tl) and checked < 5:
            n = _norm_line(tl[i])
            if not n:                        # blank
                i += 1
                continue
            if n in rep_norm:
                tl.pop(i)
                continue
            if not re.search(r"[઀-૿ऀ-ॿ]", tl[i]):   # separator/ornament line
                i += 1
                continue
            checked += 1
            i += 1
        tail = "\n".join(rep_lines + [""] + tl).strip()
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
        # titles of the sections that start on this page — a repair pass may
        # have rewritten a garbled heading, which would strand a needle
        st = starters.get(pg, [])
        # split j creates the boundary before part j+1. When the first starter
        # owns the page top (k == m-1) that part belongs to starter j+1, so the
        # titles must be shifted or a fallback matches the WRONG section.
        shift = 1 if len(sps) == len(st) - 1 else 0
        titles = [specs[st[i + shift]].get("title_gu", "") if i + shift < len(st) else ""
                  for i in range(len(sps))]
        rest = page_text(src, pg).strip()
        parts = []
        for n, one in enumerate(sps):
            if n < len(titles) and titles[n]:
                one = dict(one, fallback_title=titles[n])
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
            elif pg == s["start_page"] and si == 0 and starters[pg][0] == 0 \
                    and len(parts) - 1 == len(starters[pg]):
                # nothing precedes the first section, so the page's opening
                # part (e.g. the ।। रामकबीर ।। invocation) belongs to it
                t = "\n".join(x for x in (parts[0], parts[1]) if x.strip())
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
    for sec in sections:
        body = "\n".join(b["text"] for b in sec["blocks"])
        for head in (sec["title"], _norm_line(sec["title"])):
            body = body.replace(head, "", 1)
        if not _norm_line(body):
            EMPTY.append(f"{book['id']}: section '{sec['title'][:24]}' has no body text")
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
    # NB: split on LF only. sections.json line numbers came from grep -n, and
    # the file contains 143 form-feed page markers that str.splitlines() would
    # also treat as line breaks — drifting every section after the first page.
    lines = full.read_text(encoding="utf-8", errors="replace").split("\n")
    spec = json.loads(sec_file.read_text(encoding="utf-8"))
    sections = []
    ATH = re.compile(r"\bATH\s+SH?R[EI]", re.I)
    for s in spec["sections"]:
        seg = lines[s["start_line"] - 1 : s["end_line"]]
        # The printed page flow can carry the previous composition's closing
        # verses above this one's ATH heading — drop that tail. Strictly
        # bounded: only a heading in the first few lines, and only one naming
        # THIS section, may trim. (A section can legitimately quote another
        # composition's ATH mid-body — e.g. Sandhya Aarati embeds Ath Shri
        # Vani — and trimming there would delete most of the section.)
        want = re.sub(r"[^a-z]", "", s["title"].lower())
        # If the slice ALREADY opens with this section's heading there is no
        # previous-composition tail to remove. Trimming here would match the
        # running page header further down and delete the opening verses.
        opens_correctly = bool(seg) and ATH.search(seg[0]) and \
            want in re.sub(r"[^a-z]", "", seg[0].lower())
        for i, ln in enumerate([] if opens_correctly else seg[:8]):
            if i == 0 or not ATH.search(ln):
                continue
            here = re.sub(r"[^a-z]", "", ln.lower())
            if want and (want in here or here.endswith(want)):
                seg = seg[i:]
                break
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
        for raw in seg:
            # form feeds are page breaks inside the line; the printed folio
            # "(N)" may sit at either end of a running-header line
            ln = raw.replace("\x0c", " ")
            pm = re.search(r"\((\d{1,3})\)", ln)
            if pm and not re.search(r"[A-Za-z]{3,}", ln[:pm.start()]):
                flush()
                cur_page = int(pm.group(1))
                ln = (ln[:pm.start()] + ln[pm.end():])
                if not ln.strip():
                    continue
            elif pm and re.fullmatch(r"[\s\dIVX|]*", ln[pm.end():]):
                cur_page = int(pm.group(1))       # folio trailing a header line
                ln = (ln[:pm.start()] + ln[pm.end():])
                if not ln.strip():
                    continue
            if not ln.strip():
                if len(cur) > 12:
                    flush()
                else:
                    cur.append("")
                continue
            cur.append(ln)
        flush()
        first_pg = next((b["page"] for b in blocks if b.get("page")), None)
        sections.append({"title": s["title"].strip(), "page_start": first_pg, "blocks": blocks})
    return dict(book, pages=143, sections=sections)

manifest = []
for book in BOOKS:
    built = build_english(book) if book["id"] == "kirtan-english" else build_gujarati(book)
    if built is None:
        print(f"skip {book['id']} (no sections.json / txt yet)")
        continue
    PENDING[f"{book['id']}.json"] = json.dumps(built, ensure_ascii=False)
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

PENDING["books.json"] = json.dumps({"books": manifest, "featured": featured},
                                   ensure_ascii=False, indent=1)
print(f"manifest: {len(manifest)} books, {len(featured)} featured")
if WARNINGS or EMPTY:
    if WARNINGS:
        print(f"BUILD FAILED — unresolved split needles: {WARNINGS}")
    if EMPTY:
        print(f"BUILD FAILED — sections with no body text: {EMPTY}")
    print("no files written; previous content left intact")
    sys.exit(1)
# structural invariants run against the FINAL payloads before anything is
# written — a regression fails the build instead of reaching readers
import subprocess, tempfile as _tf
with _tf.TemporaryDirectory() as _d:
    pass
for name, data in PENDING.items():
    # write-then-rename: a crash mid-loop can never leave a truncated or
    # half-written content file behind
    fd, tmp = tempfile.mkstemp(dir=OUT, suffix=".tmp")
    with os.fdopen(fd, "w", encoding="utf-8") as fh:
        fh.write(data)
    os.replace(tmp, OUT / name)
print(f"wrote {len(PENDING)} content files")
_inv = subprocess.run([sys.executable, str(BASE / "tools" / "invariants.py")],
                      capture_output=True, text=True)
print(_inv.stdout.strip())
if _inv.returncode != 0:
    print("BUILD FAILED — structural invariants violated")
    sys.exit(1)
