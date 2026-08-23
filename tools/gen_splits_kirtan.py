#!/usr/bin/env python3
"""Generate extraction/kirtan-gujarati/splits.json — sub-page section starts.

For each section in the kirtan/sakhi volume, find the heading line inside its
start page (corrected text) and emit {"<page>": {"before": <verbatim line>}}.
Headings are explicit in this volume (।। અથ શ્રી … ।। / ।। अथ श्री … ।। or the
title itself), so this is mechanical. Pages whose heading is at the top (no
body text above it) get no entry."""

import json, re, unicodedata
from pathlib import Path

EXT = Path("/Users/harsh/RamKabir/extraction/kirtan-gujarati")
spec = json.loads((EXT / "sections.json").read_text(encoding="utf-8"))

def dev_to_guj(s):
    # Devanagari and Gujarati blocks are layout-aligned (क U+0915 → ક U+0A95)
    return "".join(chr(ord(c) + 0x180) if "ऀ" <= c <= "ॣ" else c for c in s)

def norm(s):
    return re.sub(r"[^઀-૿a-z]", "", dev_to_guj(s).lower())

def title_words(t):
    return [w for w in re.split(r"[^઀-૿ऀ-ॿ]+", dev_to_guj(t)) if len(norm(w)) >= 3]

def page_lines(pg):
    for sub in ("txt-corrected", "txt"):
        p = EXT / sub / f"page-{pg:04d}.txt"
        if p.exists():
            return p.read_text(encoding="utf-8").split("\n")
    return []

RUNNING_HEADER = norm("શ્રી અધ્યારુજીના કીર્તન")
ATH = re.compile(r"અથ|अथ")

splits, report = {}, []
for s in spec["sections"]:
    if s["idx"] < 2:
        continue
    pg = s["start_page"]
    lines = page_lines(pg)
    tnorm = norm(s["title_gu"])
    words = title_words(s["title_gu"])
    ath_lines = [i for i, ln in enumerate(lines) if ATH.search(ln)]
    # score each line as heading candidate
    best, best_score = None, 0
    for i, ln in enumerate(lines):
        lnorm = norm(ln)
        if not lnorm:
            continue
        score = 0
        if len(tnorm) >= 4 and (tnorm in lnorm or (len(lnorm) >= 4 and lnorm in tnorm)):
            score += 2
        score += sum(1 for w in words if norm(w) in lnorm)
        if ATH.search(ln):
            score += 1
        if score > best_score:
            best, best_score = i, score
    # a page whose ONLY અથ-line scored 1: અથ universally marks composition
    # starts in this volume, so accept it as the heading
    if best_score == 1 and len(ath_lines) == 1 and best == ath_lines[0]:
        best_score = 2
    if best is None or best_score < 2:
        report.append(f"idx {s['idx']} p{pg}: NO heading match ({s['title_gu'][:24]}) score={best_score}")
        continue
    # anything with letters above the heading (beyond page-no + running header)?
    above = [ln for ln in lines[:best]
             if norm(ln) and norm(ln) != RUNNING_HEADER and not re.fullmatch(r"[\s()૦-૯0-9०-९]*", ln)]
    if not above:
        report.append(f"idx {s['idx']} p{pg}: heading at top — no split")
        continue
    splits[str(pg)] = {"before": lines[best]}
    report.append(f"idx {s['idx']} p{pg}: split before line {best}: {lines[best][:40]}")

(EXT / "splits.json").write_text(json.dumps(splits, ensure_ascii=False, indent=1), encoding="utf-8")
print(f"{len(splits)} splits written")
for r in report:
    print(" ", r)
