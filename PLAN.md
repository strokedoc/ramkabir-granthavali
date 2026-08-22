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
- [ ] Verse-page fidelity pass in flight: pages 177–365 re-OCRing as Hindi
      (Devanagari sakhi text); 8 Opus agents doing image-grounded correction
      of Gujarati verse pages 23–176. OCR text stays the fallback.
- [ ] My spot-check of corrected pages vs images; rebuild; deploy
      (unlisted, noindex — decided)
