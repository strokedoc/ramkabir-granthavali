#!/usr/bin/env python3
"""Structural invariants for the built content — the regression net.

Each check encodes a defect class that actually shipped at some point, so a
recurrence fails the build instead of reaching readers. Run after every build.
Exit 1 on any violation."""

import json, os, re, sys
from pathlib import Path
import sys as _sys; _sys.path.insert(0, str(Path(__file__).resolve().parent))
from book_spec import BOOKS

BASE = Path(__file__).resolve().parents[1]
APP = Path(os.environ.get("CONTENT_DIR") or (BASE / "app" / "content"))
EXT = BASE / "extraction"
GU_BOOKS = ["samagam-purvardh", "samagam-uttarardh", "sant-darshan",
            "kirtan-gujarati", "jivandas-sakhi"]
SRC = {"jivandas-sakhi": "kirtan-gujarati"}
fails = []


def norm(s):
    return re.sub(r"\s+", "", s)


def load(book):
    return json.loads((APP / f"{book}.json").read_text(encoding="utf-8"))


# --- title-skeleton helpers: used by the cross-link check (7) and the
#     featured-chip check (12), so they are defined before either runs
_M = {"ઞ":"n","ઙ":"n","ક":"k","ખ":"k","ગ":"g","ઘ":"g","ચ":"c","છ":"c","જ":"j","ઝ":"j","ટ":"t","ઠ":"t",
      "ડ":"d","ઢ":"d","ણ":"n","ત":"t","થ":"t","દ":"d","ધ":"d","ન":"n","પ":"p","ફ":"p",
      "બ":"b","ભ":"b","મ":"m","ય":"y","ર":"r","લ":"l","વ":"v","ળ":"l","શ":"s","ષ":"s",
      "સ":"s","હ":"h"}

def skel_gu(t):
    return "".join(_M.get(c, "") for c in t)

def skel_en(t):
    t = re.sub(r"[^a-z]", "", t.lower())
    for a_, b_ in (("chh", "c"), ("ch", "c"), ("kh", "k"), ("gh", "g"), ("th", "t"),
                   ("dh", "d"), ("ph", "p"), ("bh", "b"), ("sh", "s"), ("w", "v"),
                   ("gn", "n"), ("jn", "n")):
        t = t.replace(a_, b_)
    return re.sub(r"[aeiou]", "", t)

def se_prefix(label_skel, target_skel):
    """the chip label starts with the composition name, so compare like-for-like"""
    return label_skel[:max(len(target_skel), 3)]

def consonant_overlap(a, b):
    """Order-independent consonant agreement. Calibrated on the real corpus:
    correct title/transliteration pairs score >=0.60, a swapped pair 0.27."""
    from collections import Counter
    ca, cb = Counter(a), Counter(b)
    return sum((ca & cb).values()) / max(1, max(len(a), len(b)))

# 1. No section may render empty (shipped: 4 emptied Sant Darshan sections)
for b in GU_BOOKS + ["kirtan-english"]:
    for s in load(b)["sections"]:
        body = "\n".join(x["text"] for x in s["blocks"])
        for head in (s["title"], norm(s["title"])):
            body = body.replace(head, "", 1)
        if not norm(body):
            fails.append(f"{b}: '{s['title'][:28]}' has no body text")

# 2. No heading duplicated across a section boundary (shipped: 21 then 6)
for b in GU_BOOKS:
    secs = load(b)["sections"]
    for i in range(1, len(secs)):
        prev, cur = secs[i - 1], secs[i]
        if not prev["blocks"] or not cur["blocks"]:
            continue
        tail = prev["blocks"][-1]["text"].strip().split("\n")[-1].strip()
        head = cur["blocks"][0]["text"].strip().split("\n")[0].strip()
        if tail and norm(tail) == norm(head):
            fails.append(f"{b}: '{cur['title'][:24]}' heading duplicated at boundary")

# 3. No heading repeated at the head of its own section (shipped: 21 sections)
for b in GU_BOOKS:
    for s in load(b)["sections"]:
        lines = [l for l in "\n".join(x["text"] for x in s["blocks"]).split("\n") if norm(l)]
        for i in range(min(4, len(lines))):
            for k in range(i + 1, min(i + 4, len(lines))):
                if norm(lines[i]) == norm(lines[k]) and len(norm(lines[i])) > 6 \
                        and norm(lines[i]) == norm(s["title"]):
                    fails.append(f"{b}: '{s['title'][:24]}' repeats its own heading")

# 4. Every source page is rendered exactly once per book (shipped: dropped
#    Jivandas invocation; duplicated page 156)
for b in GU_BOOKS:
    src = SRC.get(b, b)
    spec = json.loads((EXT / src / "sections.json").read_text(encoding="utf-8"))["sections"]
    # an aliased volume renders only its slice of a shared scan
    rng = next((x.get("idx_range") for x in BOOKS if x["id"] == b), None)
    if rng:
        spec = [x for x in spec if rng[0] <= x["idx"] <= rng[1]]
    j = load(b)
    seen = {x["page"] for s in j["sections"] for x in s["blocks"]}
    # the range comes from sections.json, NOT from the pages that happened to
    # render: deriving `hi` from the output cannot notice a dropped LAST page
    lo = min(x["start_page"] for x in spec)
    hi = max(x["end_page"] for x in spec)
    missing = [p for p in range(lo, hi + 1) if p not in seen]
    if missing:
        fails.append(f"{b}: pages never rendered: {missing[:6]}")
    # ...and the converse: a page from OUTSIDE this volume's range (the two
    # volumes that share a scan make this easy to do by accident) was invisible
    # to a subset-only test, and check 5 self-balances because it sums source
    # chars over whatever pages rendered
    extra = sorted(p for p in seen if not (lo <= p <= hi))
    if extra:
        fails.append(f"{b}: pages rendered that are not in this volume: {extra[:6]}")
    # page labels must not go backwards inside a section: swapping two of them
    # leaves the text byte-identical and drives both the reader's page display
    # and the per-page garble whitelist lookup
    for s_ in j["sections"]:
        pg = [x["page"] for x in s_["blocks"]]
        if pg != sorted(pg):
            fails.append(f"{b}: '{s_['title'][:24]}' has out-of-order page labels")
            break

# 5. Content conservation: rendered text must match the source pages (shipped:
#    77 chars lost to a bad fuzzy match; 8k lost in the English volume)
for b in GU_BOOKS:
    src = SRC.get(b, b)
    j = load(b)
    pages = {x["page"] for s in j["sections"] for x in s["blocks"]}
    src_chars = 0
    for p in sorted(pages):
        for sub in ("txt-corrected", "txt"):
            f = EXT / src / sub / f"page-{p:04d}.txt"
            if f.exists():
                src_chars += len(norm(f.read_text(encoding="utf-8", errors="replace")))
                break
        else:
            # a partially committed scan would otherwise just shrink the source
            # total and slip under the 3% drift allowance
            fails.append(f"{b}: source page {p} is missing from extraction/{src}")
    got = sum(len(norm(x["text"])) for s in j["sections"] for x in s["blocks"])
    # 3% was ~16k characters on the larger volumes — wide enough to hide a
    # 14,954-char deletion. Measured drift is 0.000% on ALL five books, so the
    # bound is 0.1%: still slack for header stripping, but no room to lose a
    # paragraph of scripture unnoticed.
    if src_chars and abs(got - src_chars) > src_chars * 0.001:
        pct = abs(got - src_chars) / src_chars * 100
        fails.append(f"{b}: rendered {got} chars vs {src_chars} in source ({pct:.2f}% drift)")

# 6. English volume: every section must open with its own heading (shipped:
#    the splitlines() drift put each composition's text under the wrong title)
ke = load("kirtan-english")
for s in ke["sections"]:
    first = s["blocks"][0]["text"] if s["blocks"] else ""
    key = re.sub(r"[^a-z]", "", s["title"].lower())[:10]
    if key and key not in re.sub(r"[^a-z]", "", first[:220].lower()):
        fails.append(f"kirtan-english: '{s['title']}' does not open with its own heading")

# 7. Cross-links must land on the matching composition (shipped: mislabeled
#    links after the English drift)
gu = load("kirtan-gujarati")
# bounded by BOTH volumes so a shorter one fails loudly instead of crashing
for i in range(1, min(32, len(gu["sections"]), len(ke["sections"]) + 1)):
    g, e = gu["sections"][i], ke["sections"][i - 1]
    # the two sides must be the SAME composition: compare the Gujarati title's
    # consonant skeleton against the English title's. Testing only for empty
    # blocks (as this did) merely repeated check 1 and proved nothing about
    # the pairing the reader is offered.
    gs, es = skel_gu(g["title"]), skel_en(e["title"])
    if gs and es and consonant_overlap(gs, se_prefix(es, gs)) < 0.5:
        fails.append(f"cross-link gu#{i} '{g['title'][:20]}' <-> en#{i-1} "
                     f"'{e['title'][:20]}': titles do not match")
if len(ke["sections"]) < 31:
    fails.append(f"kirtan-english has {len(ke['sections'])} sections; "
                 f"the cross-link map expects at least 31")

# 8. English editions must exist and align with their Gujarati books
for b in GU_BOOKS:
    f = APP / "en" / f"{b}.json"
    if not f.exists():
        fails.append(f"missing English edition for {b}")
        continue
    en = json.loads(f.read_text(encoding="utf-8"))
    if len(en["sections"]) != len(load(b)["sections"]):
        fails.append(f"{b}: English section count {len(en['sections'])} != Gujarati")
    for i, s in enumerate(en["sections"]):
        if s and not (s.get("translation") or s.get("translit")):
            fails.append(f"{b} en#{i}: empty English section")

# 9. English page labels must advance monotonically and match the printed range
ke_pages = [x["page"] for s in ke["sections"] for x in s["blocks"] if x.get("page")]
if ke_pages:
    if any(b < a for a, b in zip(ke_pages, ke_pages[1:])):
        fails.append("kirtan-english: page labels are not monotonic (mislabelled page)")
    if sum(1 for s in ke["sections"] for x in s["blocks"] if not x.get("page")):
        fails.append("kirtan-english: blocks without a page label")

# 10. Section ORDER must match the structure map (catches reordered/swapped
#     sections, which every content check above would otherwise accept)
for b in GU_BOOKS:
    src = SRC.get(b, b)
    spec = json.loads((EXT / src / "sections.json").read_text(encoding="utf-8"))["sections"]
    # an aliased volume renders only its slice of a shared scan
    rng = next((x.get("idx_range") for x in BOOKS if x["id"] == b), None)
    if rng:
        spec = [x for x in spec if rng[0] <= x["idx"] <= rng[1]]
    got = [s["title"] for s in load(b)["sections"]]
    if len(got) > 1 and len(spec) >= len(got):
        pages = [x["blocks"][0]["page"] for x in load(b)["sections"] if x["blocks"]]
        if any(q < p for p, q in zip(pages, pages[1:])):
            fails.append(f"{b}: sections are out of page order (reordered or swapped)")

# 11. Each English section must correspond to ITS Gujarati section, not merely
#     exist (catches two translations swapped between sections)
# Correspondence is checked by SIZE CORRELATION rather than by transliteration
# similarity: a fuzzy script comparison produced false positives on legitimate
# conjuncts (જ્ઞાનીજી -> "Gnaniji", સોરંગી -> "Sorangi"). If two translations are
# swapped between sections of different length, the ratio becomes an outlier.
for b in GU_BOOKS:
    f = APP / "en" / f"{b}.json"
    if not f.exists():
        continue
    en = json.loads(f.read_text(encoding="utf-8"))
    gu_secs = load(b)["sections"]
    ratios = []
    for i, es in enumerate(en["sections"]):
        if not es or i >= len(gu_secs):
            continue
        src_len = sum(len(x["text"]) for x in gu_secs[i]["blocks"])
        en_len = len((es.get("translation") or "") + (es.get("translit") or ""))
        if src_len > 400 and en_len > 0:
            ratios.append((en_len / src_len, i, gu_secs[i]["title"][:20]))
    weak = []
    for i, es in enumerate(en["sections"]):
        if not es or i >= len(gu_secs):
            continue
        g, e = skel_gu(gu_secs[i]["title"]), skel_en(es.get("title_translit") or "")
        if len(g) >= 3 and len(e) >= 3 and consonant_overlap(g, e) < 0.45:
            weak.append(gu_secs[i]["title"][:20])
    if weak:
        fails.append(f"{b}: {len(weak)} English section titles do not match their "
                     f"Gujarati section, e.g. {weak[:3]}")
    if len(ratios) >= 6:
        vals = sorted(r[0] for r in ratios)
        med = vals[len(vals) // 2]
        odd = [r for r in ratios if r[0] > med * 4 or r[0] < med / 4]
        if odd:                       # report ANY outlier — a two-record swap
            fails.append(f"{b}: {len(odd)} English sections are out of "        # slipped through the old allowance
                         f"proportion to their source, e.g. {[o[2] for o in odd[:3]]}")

    # EXACT correspondence via provenance signature. Fuzzy alternatives were
    # measured and rejected: title similarity passed a Vedpuran<->Vadi swap at
    # 0.80, and "title appears in its own translation" holds for only 44% of
    # legitimate pairs. The signature ties each translation to the source
    # section it was generated from, with no threshold to tune.
    import hashlib
    bad_sig = []
    for i, es in enumerate(en["sections"]):
        if i >= len(gu_secs):
            continue
        if not es:
            bad_sig.append(f"{gu_secs[i]['title'][:18]} (MISSING translation)")
            continue
        if not es.get("src_sig"):          # fail closed: no signature, no pass
            bad_sig.append(f"{gu_secs[i]['title'][:18]} (no provenance signature)")
            continue
        src_txt = "\n".join(x["text"] for x in gu_secs[i]["blocks"])
        want = hashlib.sha1(re.sub(r"\s+", "", src_txt).encode("utf-8")).hexdigest()[:12]
        if es["src_sig"] != want:
            bad_sig.append(gu_secs[i]["title"][:20])
    if bad_sig:
        fails.append(f"{b}: {len(bad_sig)} English sections are attached to the "
                     f"wrong source section, e.g. {bad_sig[:3]}")

# 12. Featured chips must point at the section they name
books_meta = json.loads((APP / "books.json").read_text(encoding="utf-8"))
for fchip in books_meta.get("featured", []):
    secs = load(fchip["book"])["sections"]
    if fchip["section"] >= len(secs):
        fails.append(f"featured chip '{fchip['label_en']}' points past the end of {fchip['book']}")
        continue
    title = secs[fchip["section"]]["title"]
    # the chip must name the section it opens, in either script
    g = skel_gu(title) or skel_en(title)   # Latin-titled volumes use the same skeleton
    e = skel_en(fchip["label_en"]) or re.sub(r"[^a-z]", "", fchip["label_en"].lower())
    if norm(title) not in norm(fchip["label_gu"]) and \
       consonant_overlap(g, se_prefix(e, g)) < 0.6:
        fails.append(f"featured chip '{fchip['label_en']}' does not point at '{title}'")

# 12b. Translation completeness. A pass that worked from OCR alone left 14
#      sections cut mid-sentence (their tails displaced into the NEXT section)
#      and 136 "[unclear]" markers, many on text that is perfectly legible on
#      the page. Neither was visible to any structural check.
import unicodedata as _ud
for b in GU_BOOKS:
    f = APP / "en" / f"{b}.json"
    if not f.exists():
        continue
    for i, s_ in enumerate(json.loads(f.read_text(encoding="utf-8"))["sections"]):
        if not s_:
            continue
        t = (s_.get("translation") or "").strip()
        if not t:
            continue
        if re.search(r"\[text continues|continues on the next page|text ends here", t, re.I):
            fails.append(f"{b} en#{i}: translation defers its ending to another section")
        # a trailing list/index entry legitimately has no terminal mark, so only
        # a sentence that simply stops is reported
        last = t.splitlines()[-1].strip()
        if not re.search(r"[.!?\"'\)\]|]$", last) and not re.search(r"\d\s*$", last):
            fails.append(f"{b} en#{i}: translation ends mid-sentence ({last[-40:]!r})")

# 13. Published set must match the integrity manifest written at publish time
#     (detects a corpus left mixed by a crash between file renames)
intg = BASE / "tools" / "integrity.json"
if os.environ.get("CONTENT_DIR"):
    pass                      # staged tree has no manifest yet; checked post-publish
elif not intg.exists():
    fails.append("integrity manifest missing — run tools/build_content.py")
else:
    import hashlib as _h
    for name, want in json.loads(intg.read_text(encoding="utf-8")).items():
        f = APP / name
        if not f.exists():
            fails.append(f"integrity: {name} is missing from the published set")
        elif _h.sha256(f.read_bytes()).hexdigest()[:16] != want:
            fails.append(f"integrity: {name} does not match the manifest "
                         f"(partial publish or out-of-band edit)")
    # the manifest is a whitelist, not just a checksum list: a file added to
    # app/content that no manifest entry names would otherwise ship unexamined
    named = set(json.loads(intg.read_text(encoding="utf-8")))
    for f in APP.rglob("*.json"):
        rel = f.relative_to(APP).as_posix()
        if rel not in named:
            fails.append(f"integrity: {rel} is published but not in the manifest")

if fails:
    print(f"INVARIANTS FAILED ({len(fails)}):")
    for f in fails:
        print("  ", f)
    sys.exit(1)
# the banner counts the check blocks that actually RAN: the manifest check is
# skipped on a staged tree, and claiming 15 when 12 ran is the kind of quiet
# over-report these gates exist to prevent
_ran = 13 - (1 if os.environ.get("CONTENT_DIR") else 0)
print(f"INVARIANTS OK — {_ran} checks across 6 books"
      + ("  (staged: manifest checked post-publish)" if os.environ.get("CONTENT_DIR") else ""))
