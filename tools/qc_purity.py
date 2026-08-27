#!/usr/bin/env python3
"""Script-purity QC gate.

1. Gujarati corpus (built books): no Latin letter runs (len>=2) in body text.
2. English edition (content/en/*.json): no Gujarati/Devanagari codepoints.
3. teachings.json: *_en / *_translit / body_en fields pure Latin;
   teachings-gu.json: no Latin runs.
Exit 1 on any violation. Run after every content rebuild."""

import json, re, sys
from pathlib import Path

APP = Path("/Users/harsh/RamKabir/app/content")
LAT = re.compile(r"[A-Za-z]{2,}")
NAT = re.compile(r"[ऀ-ॿ઀-૿]")
fails = []

# Latin in the Gujarati books is checked by tools/find_garble.py against the
# evidence-based whitelist (tokens confirmed present in the printed page by an
# image-verification worker). No blanket baseline: unverified Latin = failure.
import subprocess
r = subprocess.run([sys.executable, "/Users/harsh/RamKabir/tools/find_garble.py"],
                   capture_output=True, text=True)
print(r.stdout.strip())
if r.returncode != 0:
    fails.append("garble detector reports unverified Latin / malformed Indic text")

en_dir = APP / "en"
for f in sorted(en_dir.glob("*.json")) if en_dir.exists() else []:
    j = json.loads(f.read_text(encoding="utf-8"))
    bad = 0
    for s in j.get("sections", []):
        if not s:
            continue
        for k in ("title_translit", "title_en", "translit", "translation"):
            bad += len(NAT.findall(s.get(k) or ""))
    if bad:
        fails.append(f"en/{f.name}: {bad} native chars in English fields")
    print(f"en/{f.name}: native-chars={bad}")

# index.html chrome: any Indic text there is baked in and cannot switch
# language at runtime (the nav "search" icon was literally the word શોધ)
html = Path("/Users/harsh/RamKabir/app/index.html").read_text(encoding="utf-8")
chrome = re.sub(r"<title>.*?</title>", "", html, flags=re.S)
chrome = re.sub(r'(aria-label|content|placeholder)="[^"]*"', "", chrome)
chrome = re.sub(r"<h1[^>]*>.*?</h1>", "", chrome, flags=re.S)
# elements marked data-i18n are language defaults that applyLang() rewrites
chrome = re.sub(r"<(\w+)[^>]*\bdata-i18n\b[^>]*>.*?</\1>", "", chrome, flags=re.S)
baked = NAT.findall(re.sub(r"<[^>]+>", " ", chrome))
if baked:
    fails.append(f"index.html bakes Indic text into language-switchable chrome: {''.join(baked)[:60]}")
print(f"index.html baked-Indic chrome chars: {len(baked)}")

tj = json.loads((APP / "teachings.json").read_text(encoding="utf-8"))
leaks = []
def scan(o, path):
    if isinstance(o, dict):
        for k, v in o.items(): scan(v, path + "." + k)
    elif isinstance(o, list):
        for i, v in enumerate(o): scan(v, f"{path}[{i}]")
    elif isinstance(o, str):
        base = re.sub(r"\[\d+\]$", "", path)
        if (base.endswith("_en") or base.endswith("_translit") or base.endswith("body_en")) and NAT.search(o):
            leaks.append(path)
scan(tj, "")
if leaks:
    fails.append(f"teachings.json native-in-EN: {leaks}")
print(f"teachings.json EN-field leaks: {len(leaks)}")

tg = json.loads((APP / "teachings-gu.json").read_text(encoding="utf-8"))
gl = []
def scan_gu(o):
    if isinstance(o, dict):
        for k, v in o.items():
            scan_gu(v)
    elif isinstance(o, list):
        for v in o: scan_gu(v)
    elif isinstance(o, str):
        gl.extend(LAT.findall(o))
scan_gu(tg)
if gl:
    fails.append(f"teachings-gu.json Latin runs: {gl[:8]}")
print(f"teachings-gu.json latin-runs: {len(gl)}")

if fails:
    print("\nFAIL:")
    for f in fails: print("  ", f)
    sys.exit(1)
print("\nPURITY OK")
