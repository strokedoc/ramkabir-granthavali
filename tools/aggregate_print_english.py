#!/usr/bin/env python3
"""Aggregate per-page印 whitelists written by the image-verification workers
(extraction/<book>/print_english/page-NNNN.json) into tools/print_english.json.

This REPLACES the old frozen "latin_baseline.json", which was created from the
then-current text and therefore blessed genuine garble it had never inspected.
Only tokens a worker confirmed against the printed page get whitelisted."""
import json
from pathlib import Path

EXT = Path('/Users/harsh/RamKabir/extraction')
BOOK_SRC = {  # books whose pages come from another book's scan
    'jivandas-sakhi': 'kirtan-gujarati',
}
out = {}
for d in sorted(EXT.glob('*/print_english')):
    book = d.parent.name
    per = {}
    for f in sorted(d.glob('page-*.json')):
        try:
            toks = json.loads(f.read_text(encoding='utf-8'))
        except Exception:
            continue
        if toks:
            per[str(int(f.stem.split('-')[1]))] = sorted(set(toks))
    if per:
        out[book] = per
for alias, src in BOOK_SRC.items():
    if src in out:
        out[alias] = out[src]
Path('/Users/harsh/RamKabir/tools/print_english.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print({b: len(v) for b, v in out.items()}, '->', sum(len(v) for v in out.values()), 'pages whitelisted')
