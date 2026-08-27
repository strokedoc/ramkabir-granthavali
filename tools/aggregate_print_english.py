#!/usr/bin/env python3
"""Aggregate per-page印 whitelists written by the image-verification workers
(extraction/<book>/print_english/page-NNNN.json) into tools/print_english.json.

This REPLACES the old frozen "latin_baseline.json", which was created from the
then-current text and therefore blessed genuine garble it had never inspected.
Only tokens a worker confirmed against the printed page get whitelisted."""
import json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

EXT = BASE / "extraction"
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
            # short tokens (<=2 chars) get a budget = how many times they occur
            # in the page text the worker verified. A later OCR insertion of an
            # extra 'X' then exceeds the budget and is flagged.
            # every approval carries a budget = its verified occurrence count,
            # so a repeated OCR artifact can never hide behind a real word
            entry = []
            for tk in sorted(set(ok)):
                # count BOUNDARY occurrences; an approval that never appears as
                # a standalone token is a worker error, not a licence
                n = len(re.findall(r'(?<![A-Za-z])' + re.escape(tk) + r'(?![A-Za-z])', page_txt))
                if n == 0:
                    rejected.append(f'{book} p{pg}: {tk!r} has no standalone occurrence')
                    continue
                entry.append({"t": tk, "n": n})
            if entry:
                per[pg] = entry
    if per:
        out[book] = per
# an aliased book shares its source scan but renders only part of it: copy just
# the pages it actually contains, so approvals land on the right namespace
ALIAS_PAGES = {'jivandas-sakhi': range(177, 366)}
for alias, src in BOOK_SRC.items():
    if src in out:
        rng = ALIAS_PAGES.get(alias)
        out[alias] = {p: v for p, v in out[src].items()
                      if rng is None or int(p) in rng}
        if rng is not None:
            out[src] = {p: v for p, v in out[src].items() if int(p) not in rng}
TARGET = BASE / "tools/print_english.json"
payload = json.dumps(out, ensure_ascii=False, indent=1)
# --check proves the SHIPPED whitelist was derived from the per-page files the
# image workers wrote. Without it a commit could add an approval by hand and
# the garble gate would strip real garble before ever scanning it.
if "--check" in sys.argv:
    have = TARGET.read_text(encoding="utf-8") if TARGET.exists() else ""
    if have.strip() != payload.strip():
        print("WHITELIST MISMATCH — tools/print_english.json does not match the "
              "per-page approvals in extraction/*/print_english/. Re-run this "
              "tool without --check and review the diff.")
        sys.exit(1)
    print("whitelist OK — derived from", sum(len(v) for v in out.values()), "verified pages")
    sys.exit(0)
TARGET.write_text(payload, encoding='utf-8')
print({b: len(v) for b, v in out.items()}, '->', sum(len(v) for v in out.values()), 'pages whitelisted')
allt = sorted({(t['t'] if isinstance(t, dict) else t)
                for v in out.values() for toks in v.values() for t in toks})
print(f'{len(allt)} distinct whitelisted tokens:', allt[:40])
if rejected:
    print(f'REJECTED {len(rejected)} entries:')
    for r in rejected[:20]: print('  ', r)
