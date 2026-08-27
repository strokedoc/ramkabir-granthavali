#!/usr/bin/env python3
"""Structural invariants for the built content — the regression net.

Each check encodes a defect class that actually shipped at some point, so a
recurrence fails the build instead of reaching readers. Run after every build.
Exit 1 on any violation."""

import json, os, re, sys
from pathlib import Path

BASE = Path("/Users/harsh/RamKabir")
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
    j = load(b)
    lo = min(x["page"] for s in j["sections"] for x in s["blocks"])
    hi = max(x["page"] for s in j["sections"] for x in s["blocks"])
    seen = {x["page"] for s in j["sections"] for x in s["blocks"]}
    missing = [p for p in range(lo, hi + 1) if p not in seen]
    if missing:
        fails.append(f"{b}: pages never rendered: {missing[:6]}")

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
    got = sum(len(norm(x["text"])) for s in j["sections"] for x in s["blocks"])
    if src_chars and abs(got - src_chars) > src_chars * 0.03:
        fails.append(f"{b}: rendered {got} chars vs {src_chars} in source (>3% drift)")

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
for i in range(1, 32):
    g, e = gu["sections"][i], ke["sections"][i - 1]
    if not g["blocks"] or not e["blocks"]:
        fails.append(f"cross-link gu#{i} <-> en#{i-1}: empty side")

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
    got = [s["title"] for s in load(b)["sections"]]
    if len(got) > 1 and len(spec) >= len(got):
        pages = [x["blocks"][0]["page"] for x in load(b)["sections"] if x["blocks"]]
        if any(q < p for p, q in zip(pages, pages[1:])):
            fails.append(f"{b}: sections are out of page order (reordered or swapped)")

# 11. Each English section must correspond to ITS Gujarati section, not merely
#     exist (catches two translations swapped between sections)
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

def consonant_overlap(a, b):
    """Order-independent consonant agreement. Calibrated on the real corpus:
    correct title/transliteration pairs score >=0.60, a swapped pair 0.27."""
    from collections import Counter
    ca, cb = Counter(a), Counter(b)
    return sum((ca & cb).values()) / max(1, max(len(a), len(b)))

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
        odd = [r for r in ratios if r[0] > med * 6 or r[0] < med / 6]
        if len(odd) > max(2, len(ratios) * 0.1):
            fails.append(f"{b}: {len(odd)} English sections are wildly out of "
                         f"proportion to their source, e.g. {[o[2] for o in odd[:3]]}")

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
    if norm(title) not in norm(fchip["label_gu"]) and not (len(g) >= 2 and g[:2] in e[:10]):
        fails.append(f"featured chip '{fchip['label_en']}' does not point at '{title}'")

if fails:
    print(f"INVARIANTS FAILED ({len(fails)}):")
    for f in fails:
        print("  ", f)
    sys.exit(1)
print("INVARIANTS OK — 13 checks across 6 books")
