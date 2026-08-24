# RamKabir PWA — Plan (2026-08-21)

App for family & friends: the Ram Kabir sampraday (Uda Bhakt) books on a phone —
readable, searchable, installable, works offline.

## Source books (all in this folder)

| Book | Pages | State |
|---|---|---|
| Samagam (Purvardh) — "Full Content" | 358 | Scanned images → OCR |
| Samagam Uttarardh (Kiran Rana) | 403 | Scanned images → OCR |
| Sant Darshan | 176 | Legacy non-Unicode font → OCR from rendered pages |
| Adhyaruji na Kirtan (Gujarati) | 365 | Scanned images → OCR |
| Adhyaruji na Kirtan (English translit) | 143 | Clean text layer → extracted ✓ |

## Extraction pipeline (validated 2026-08-21)

1. **OCR (running):** `extraction/ocr_run.sh` — pdftoppm 300dpi → tesseract `guj+eng`
   → `extraction/<book>/txt/page-NNNN.txt`. Resumable (re-run skips done pages).
   Pilot check: tesseract near-perfect on this clean print; Haiku *vision* transcription
   was clearly worse (garbled names/dates) — decided: OCR mechanically, use lower
   models only for text-level structuring.
2. **Structuring (next session, Haiku/Sonnet subagents):** feed OCR text in chunks;
   output JSON per book: sections (kirtan/ras/sakhi/chapter boundaries), titles,
   verse numbers, page mapping, obvious-OCR-error cleanup. English kirtan gets
   aligned to Gujarati kirtan by ras/verse number where possible.
3. **Index build:** one `content/<book>.json` per book + a search index with
   Gujarati text AND roman transliteration (family members who can't type Gujarati
   can search "ganpati", "hari hari").

## App (decided — simplest thing that fully solves it)

- **Static PWA, no backend, no accounts.** Pure HTML/JS/CSS + JSON content,
  service worker for offline + install-to-home-screen. Zero running cost.
- **Screens:** Library (5 books) → book contents (list of kirtans/chapters) →
  Reader (verse-aware layout, adjustable Gujarati font size, dark mode,
  Gujarati/English toggle for the kirtans that have both) → Search (script +
  transliteration) → Bookmarks/favorites (localStorage).
- **Hosting:** Cloudflare Pages or GitHub Pages private-ish link — Harsh decides
  when/where to share (outward-facing call).

## Sharing scope — DECIDED (Harsh, 2026-08-21)

No password protection. Plain unlisted link, `noindex` so search engines don't
list it. (Context that prompted the question: Samagam p.5 Purvardh instructs not
to present the kirtans to non-adhikari; Harsh decided an open family link is fine.)

## Status

- [x] PDFs inspected, pilot OCR validated, English book extracted
- [x] Community research brief done (see extraction/research-brief.md)
- [x] Full OCR — all 4 Gujarati books done (~4M chars total), spot-checked
- [x] PWA built (`app/`) and verified on mobile viewport: library, TOC, reader,
      cross-script search (ganpati ⇄ ગણપતિ), bookmarks, dark mode, offline SW
- [x] Structuring: kirtan-english (Sonnet, 33 sections), samagam-purvardh
      (Opus, 13 sections; scan contains ~14 pages of the Kirtan book's front
      matter by mistake — collapsed into one front-matter entry)
- [x] Structuring done for ALL books (Opus): uttarardh 16 ch (no front matter,
      continues purvardh mid-sentence); kirtan-gujarati = TWO bound works →
      split into "અધ્યારુજીનાં કીર્તન" (38) + "વૈષ્ણવ જીવણદાસજીકી સાખી" (26);
      sant-darshan 96 (TOC had 4 page errors, corrected against page images)
- [x] App now has 6 books (was 5 — the sakhi work was a discovery)
- [x] Verse fidelity DONE: entire kirtan+sakhi volume (pages 23–365, 343 pages)
      image-ground-corrected by Opus agents; spot-checked by Fable against
      page images (p43, p100, p250). Devanagari pages re-OCR'd as Hindi first.
- [x] સાર (Essence) teaching layer: 8 pearls / 4 themes + Our Story +
      Today's Pearl; authoring pipeline in tools/TEACHINGS_GUIDE.md
- [x] DEPLOYED: https://strokedoc.github.io/ramkabir-granthavali/
      (GitHub Pages via Actions; repo strokedoc/ramkabir-granthavali;
      push to main = redeploy; bump sw.js VERSION each content change)
- [x] Sub-page chapter boundaries across ALL books (2026-08-22/23): boundary
      pages split at the printed heading line (splits.json per book; Sant
      Darshan needed 63 split points + 18 heading repairs; p145 rebuilt from
      image). App-wide ગુ/EN language toggle + kirtan gu⇄en cross-links.
- [ ] Harsh: read-through of સાર pearl wording before wide family sharing
- [ ] Later (optional): verse-quote correction inside Samagam volumes;
      sub-headings pass for Samagam ch. 13/17; more pearls (વેદપુરાણ theme)
