#!/usr/bin/env python3
"""Aggregate per-page印 whitelists written by the image-verification workers
(extraction/<book>/print_english/page-NNNN.json) into tools/print_english.json.

This REPLACES the old frozen "latin_baseline.json", which was created from the
then-current text and therefore blessed genuine garble it had never inspected.
Only tokens a worker confirmed against the printed page get whitelisted."""
import json, re, sys
from pathlib import Path

EXT = Path('/Users/harsh/RamKabir/extraction')
rejected = []

def page_text(book, n):
    for sub in ('txt-corrected', 'txt'):
        f = EXT / book / sub / f'page-{n:04d}.txt'
        if f.exists():
            return f.read_text(encoding='utf-8', errors='replace')
    return ''
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
            rejected.append(f'{book}/{f.name}: unparseable'); continue
        if not isinstance(toks, list):
            rejected.append(f'{book}/{f.name}: not a list'); continue
        pg = str(int(f.stem.split('-')[1]))
        page_txt = page_text(book, int(pg))
        ok = []
        for tk in toks:
            # a whitelist entry must be a plausible token AND actually occur on
            # the page — otherwise a stray entry could hide garble forever
            if not isinstance(tk, str) or not re.fullmatch(r"[A-Za-z][A-Za-z.&'/-]{0,30}", tk):
                rejected.append(f'{book} p{pg}: bad token {tk!r}'); continue
            if tk not in page_txt:
                rejected.append(f'{book} p{pg}: {tk!r} not present on page'); continue
            ok.append(tk)
        if ok:
            per[pg] = sorted(set(ok))
    if per:
        out[book] = per
for alias, src in BOOK_SRC.items():
    if src in out:
        out[alias] = out[src]
Path('/Users/harsh/RamKabir/tools/print_english.json').write_text(
    json.dumps(out, ensure_ascii=False, indent=1), encoding='utf-8')
print({b: len(v) for b, v in out.items()}, '->', sum(len(v) for v in out.values()), 'pages whitelisted')
allt = sorted({t for v in out.values() for toks in v.values() for t in toks})
print(f'{len(allt)} distinct whitelisted tokens:', allt[:40])
if rejected:
    print(f'REJECTED {len(rejected)} entries:')
    for r in rejected[:20]: print('  ', r)
