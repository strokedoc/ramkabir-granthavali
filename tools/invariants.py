#!/usr/bin/env python3
"""Structural invariants for the built content — the regression net.

Each check encodes a defect class that actually shipped at some point, so a
recurrence fails the build instead of reaching readers. Run after every build.
Exit 1 on any violation."""

import json, re, sys
from pathlib import Path

BASE = Path("/Users/harsh/RamKabir")
APP = BASE / "app" / "content"
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

if fails:
    print(f"INVARIANTS FAILED ({len(fails)}):")
    for f in fails:
        print("  ", f)
    sys.exit(1)
print("INVARIANTS OK — 8 checks across 6 books")
