# English edition — worker instructions

You produce the English edition of sections of Ram Kabir sampraday books (Gujarati/Devanagari originals). You receive: book id, mode, and units — each unit = {sec (section index), title, pages (page numbers), part, parts}.

## Getting the source text
The built content is authoritative (already boundary-split). For each unit run:
```bash
python3 -c "
import json,sys
j=json.load(open('/Users/harsh/RamKabir/app/content/<BOOK>.json'))
s=j['sections'][<SEC>]
for b in s['blocks']:
    if b['page'] in <PAGES>: print('== page',b['page'],'==');print(b['text'])
"
```

## Output — one JSON file per unit
Write to `/Users/harsh/RamKabir/extraction/en/<book>/s<sec>-p<part>.json` (create dirs):
```json
{
  "book": "...", "sec": N, "part": N, "parts": N,
  "title_translit": "<pronunciation of the section title in Latin letters>",   // part 1 only
  "title_en": "<short English meaning of the title>",                          // part 1 only
  "translit": "<see modes>",
  "translation": "<see modes>"
}
```

## Modes
- **prose**: `translation` only (`translit`: empty string). Translate the Gujarati prose faithfully into clear, plain modern English. Keep paragraph breaks. Keep verse quotations embedded in the prose as: transliterated line(s) in *italics markers* (surround with _underscores_) followed by their English meaning in parentheses. Do not summarize, do not skip sentences, do not embellish.
- **verse-full**: `translit` = line-by-line Latin-script pronunciation of the verse text, same line order as the original, verse numbers as ||1||. `translation` = couplet-by-couplet English meaning, numbered to match (1., 2., …). Cover EVERY couplet in your pages — no sampling.
- **verse-explain**: `translation` only — couplet-by-couplet (or stanza-by-stanza) English meaning for your pages, numbered to match the printed verse numbers. (`translit` empty — a printed transliteration already exists.)

## Non-negotiable rules
1. **Script purity: `title_translit`, `translit`, and `translation` must contain ZERO Gujarati (U+0A80–U+0AFF) or Devanagari (U+0900–U+097F) characters.** Dandas become "|" and "||"; ॥૧॥ becomes ||1||. Verify before writing: `python3 -c "import re,sys; t=open('<file>').read(); sys.exit(1 if re.search(r'[ऀ-ॿ઀-૿]', t) else 0)"`.
2. Transliteration convention: simple readable roman as used in the community's own printed English edition (e.g. "Parbrahm vani re parni e"; sh for શ/ષ, ch/chh, no diacritics). Proper nouns: Jivanji, Adhyaruji, Ramkabir, Puniyad.
3. Translation is faithful — no added theology, no omissions. Genuinely unclear/garbled source → "[unclear]" at that spot, never a guess.
4. Skip nothing in your assigned pages; if a page's text is a running header/folio only, note nothing and move on.
5. Keep spiritual terms as terms with a one-time gloss: bhakti (devotion), satsang (holy company), parayan (recitation), sakhi (couplet), kirtan (hymn).
6. Front-matter units (title pages, publisher info): translate the meaningful content (dedication, preface); one-line entries like addresses may be rendered directly.

Final response: one line per unit: `s<sec>-p<part>: written | problem: <what>`. Nothing else.
