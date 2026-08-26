#!/usr/bin/env python3
"""Detect likely OCR garble in the built Gujarati/Devanagari content.

Two independent signals, neither of which needs the page image:
 A) any Latin run (the print's own English is whitelisted per page by
    tools/print_english.json once a page has been image-verified)
 B) malformed Indic sequences — a matra where no matra can go, a halant at
    a word end, stacked matras, orphan signs. These cannot occur in correctly
    typeset Gujarati/Devanagari, so each hit is a transcription defect.
Outputs a ranked page list for image verification."""
import json, re, sys
from pathlib import Path

APP = Path('/Users/harsh/RamKabir/app/content')
BOOKS = ['samagam-purvardh','samagam-uttarardh','sant-darshan','kirtan-gujarati','jivandas-sakhi']
LAT = re.compile(r'[A-Za-z]{2,}')
CONS = r'ક-હক-হक-ह'
MATRA = r'ા-ૌा-ौ'
ANUS = r'ઁ-ઃँ-ः'
HAL = r'્्'
BAD = [
    (re.compile(f'[{MATRA}]{{2,}}'), 'stacked matras'),
    (re.compile(f'(?<![{CONS}{MATRA}{ANUS}{HAL}])[{MATRA}]'), 'orphan matra'),
    # A halant at word end is VALID (અર્થાત્, ભગવદ્‌, विद्युत् …) — only a halant
    # followed by a matra/another halant, or one opening a word, is malformed.
    (re.compile(f'[{HAL}][{MATRA}{HAL}]'), 'halant fault'),
    (re.compile(f'(?<![{CONS}{MATRA}{ANUS}])[{HAL}]'), 'orphan halant'),
    (re.compile(f'[{ANUS}][{MATRA}]'), 'sign-order fault'),
]

whitelist = {}
wl_file = Path('/Users/harsh/RamKabir/tools/print_english.json')
if wl_file.exists():
    whitelist = json.loads(wl_file.read_text())

rows = []
for b in BOOKS:
    j = json.loads((APP / f'{b}.json').read_text(encoding='utf-8'))
    per_page = {}
    for s in j['sections']:
        for bl in s['blocks']:
            pg = str(bl['page'])
            t = bl['text']
            hits = per_page.setdefault(pg, {'latin': [], 'indic': []})
            allowed = set(whitelist.get(b, {}).get(pg, []))
            for w in LAT.findall(t):
                if w not in allowed:
                    hits['latin'].append(w)
            for rx, name in BAD:
                for m in rx.finditer(t):
                    frag = t[max(0, m.start()-12):m.end()+12].replace('\n', ' ')
                    hits['indic'].append(f'{name}: …{frag}…')
    for pg, h in sorted(per_page.items(), key=lambda kv: int(kv[0])):
        n = len(h['latin']) + len(h['indic'])
        if n:
            rows.append({'book': b, 'page': int(pg), 'n': n,
                         'latin': h['latin'][:8], 'indic': h['indic'][:4]})

rows.sort(key=lambda r: -r['n'])
json.dump(rows, open('/Users/harsh/RamKabir/tools/garble_report.json', 'w'), ensure_ascii=False, indent=1)
by_book = {}
for r in rows:
    by_book.setdefault(r['book'], [0, 0])
    by_book[r['book']][0] += 1
    by_book[r['book']][1] += r['n']
for b, (pages, n) in by_book.items():
    print(f'{b}: {pages} suspect pages, {n} hits')
print(f'TOTAL: {len(rows)} pages')
for r in rows[:6]:
    print(' ', r['book'], r['page'], r['n'], (r['latin'] or r['indic'])[:4])
sys.exit(1 if rows else 0)
