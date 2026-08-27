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
from collections import Counter
from pathlib import Path

APP = Path('/Users/harsh/RamKabir/app/content')
BOOKS = ['samagam-purvardh','samagam-uttarardh','sant-darshan','kirtan-gujarati','jivandas-sakhi']
LAT = re.compile(r'[A-Za-z]{2,}')
CONS = r'ક-હক-হक-ह'
MATRA = r'ા-ૌा-ौ'
ANUS = r'ઁ-ઃँ-ः'
HAL = r'્्'
BAD = [
    # Genuine printed forms that only LOOK like stacked matras:
    #   ર+ૂ+ા     → the રૂા. (rupees) ligature
    #   digit+ાા  → traditional Gujarati fraction mark (૪ાા = 4½)
    (re.compile(f'(?<![૦-૯0-9])(?<!ર)(?<!र)(?!ૂા(?![{MATRA}])|ूा(?![{MATRA}]))[{MATRA}]{{2,}}'),
     'stacked matras'),
    (re.compile(f'(?<=[૦-૯0-9])(?!ાા(?![{MATRA}]))[{MATRA}]'), 'bad digit matra'),
    # (digits may legitimately carry the fraction matra pair — checked above)
    (re.compile(f'(?<![{CONS}{MATRA}{ANUS}{HAL}૦-૯0-9०-९\u200c\u200d])[{MATRA}]'), 'orphan matra'),
    # A halant at word end is VALID (અર્થાત્, ભગવદ્‌, विद्युत् …) — only a halant
    # followed by a matra/another halant, or one opening a word, is malformed.
    # halant + (optional joiner) + matra/halant is malformed in every case
    (re.compile(f'[{HAL}][\u200c\u200d]?[{MATRA}{HAL}]'), 'halant fault'),
    (re.compile(f'(?<![{CONS}])[{HAL}]'), 'orphan halant'),
    (re.compile(f'[{ANUS}][{MATRA}]'), 'sign-order fault'),
]

whitelist = {}
wl_file = Path('/Users/harsh/RamKabir/tools/print_english.json')
if wl_file.exists():
    whitelist = json.loads(wl_file.read_text())
# Indic forms an image-verification worker confirmed the book really prints
# (e.g. કૃીપાનાથ in samagam-uttarardh p163/164 — the manuscript's own spelling)
indic_ok = {}
ind_file = Path('/Users/harsh/RamKabir/tools/print_indic.json')
if ind_file.exists():
    indic_ok = json.loads(ind_file.read_text())

rows = []
for b in BOOKS:
    j = json.loads((APP / f'{b}.json').read_text(encoding='utf-8'))
    per_page = {}
    for s in j['sections']:
        for bl in s['blocks']:
            pg = str(bl['page'])
            t = bl['text']
            hits = per_page.setdefault(pg, {'latin': [], 'indic': []})
            # Whitelisting is TOKEN-BOUNDARY based, and a composite entry is a
            # phrase — it never blesses its parts elsewhere:
            #   "Apple"             -> the word Apple is genuine on this page
            #   "www.ramkabir.guru" -> that exact string is genuine; a stray
            #                          "guru" elsewhere is still flagged
            # (substring removal was unsound: "in"+"for" erased "infor")
            words, phrases, budget = set(), [], {}
            for entry in whitelist.get(b, {}).get(pg, []):
                if isinstance(entry, dict):      # short token with a count budget
                    budget[entry["t"]] = entry["n"]
                    if re.fullmatch(r'[A-Za-z]+', entry["t"]):
                        words.add(entry["t"])
                    else:
                        phrases.append(entry["t"])
                elif re.fullmatch(r'[A-Za-z]+', entry):
                    words.add(entry)
                else:
                    phrases.append(entry)
            # phrase removal is BOUNDARY-AWARE: an approved URL glued to a
            # stray letter ("www.ramkabir.guruX") must not be erased
            scan = t
            # budgeted phrases (M.A., infor-) are removed only as many times as
            # the verified page actually contains them
            for ph in sorted([x for x in phrases if x in budget], key=len, reverse=True):
                scan = re.sub(r'(?<![A-Za-z઀-૿ऀ-ॿ])' + re.escape(ph) + r'(?![A-Za-z઀-૿ऀ-ॿ])',
                              ' ', scan, count=budget[ph])
            for ph in sorted([x for x in phrases if x not in budget], key=len, reverse=True):
                scan = re.sub(r'(?<![A-Za-z઀-૿ऀ-ॿ])' + re.escape(ph) + r'(?![A-Za-z઀-૿ऀ-ॿ])',
                              ' ', scan)
            seen_word = {}
            for w in LAT.findall(scan):
                seen_word[w] = seen_word.get(w, 0) + 1
                if w not in words or (w in budget and seen_word[w] > budget[w]):
                    hits['latin'].append(w)
            # a lone Latin letter left in Indic text is a transcription artifact
            seen_short = {}
            for m in re.finditer(r'(?<![A-Za-z])[A-Za-z](?![A-Za-z])', scan):
                tok = m.group(0)
                seen_short[tok] = seen_short.get(tok, 0) + 1
                allowed = budget.get(tok, 0) if tok in words else 0
                if tok not in words or seen_short[tok] > allowed:
                    hits['latin'].append(tok)
            # an immediately repeated Latin token is garble even when the word
            # itself is genuinely printed ("Apple Apple")
            for m in re.finditer(r'\b([A-Za-z]{2,})\s+\1\b', t):
                hits['latin'].append(m.group(0))
            ok_forms = indic_ok.get(b, {}).get(pg, [])
            ok_spans = []
            for f in ok_forms:            # exact character ranges of approved forms
                start = t.find(f)
                while start != -1:
                    ok_spans.append((start, start + len(f)))
                    start = t.find(f, start + 1)
            for rx, name in BAD:
                for m in rx.finditer(t):
                    if any(a <= m.start() and m.end() <= b_ for a, b_ in ok_spans):
                        continue
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
