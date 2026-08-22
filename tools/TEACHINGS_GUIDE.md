# સાર (Essence) — authoring guide for teaching content

The સાર tab is driven entirely by `app/content/teachings.json`. Adding new
pearls — including from books Harsh shares later — never requires touching
app code.

## The non-negotiable rules (in priority order)

1. **Every unit anchors on a verbatim verse** from an extracted book, verified
   against the page image (or a corrected `txt-corrected/` page). Never quote
   from memory or from the web.
2. **Let the books interpret each other.** Where the tradition's own
   commentary exists (Samagam explains the kirtans; prefaces explain the
   sakhis), the `why_en` should carry *its* explanation, quoted or closely
   paraphrased — not our theology.
3. **Plain meaning, no sermonizing.** `meaning_en` says what the verse says,
   in the words a 16-year-old cousin would understand. One reflection
   question, concrete, first-person.
4. **Every unit deep-links back** (`source.book` + `source.section` = the
   app's section index in that book's content JSON) so understanding flows
   into reading.

## Adding a new book's pearls (the pipeline)

1. Extract the book: OCR via `extraction/ocr_run.sh` pattern (tesseract
   `guj+eng`; check for Devanagari pages — see `reocr_script_check.sh`).
2. Structure it: Opus agent maps sections → `sections.json` (see the prompts
   used in the 2026-08-21 session; verify headings against page images).
3. Register it in `tools/build_content.py` BOOKS list; run the script.
4. Read the book (or targeted chapters), select 2–6 verses that carry its
   essence, verify each against the page image.
5. Append units to `teachings.json` — join an existing theme or add a new
   one. Bump `"version"`, and bump `VERSION` in `app/sw.js` so installed
   phones refresh.

## Unit schema

```json
{
  "id": "kebab-slug",
  "title_gu": "…", "title_en": "…",
  "verse_gu": "line1\nline2 ॥૧॥",
  "verse_translit": "…",
  "source": { "book": "<book-id>", "section": <int>, "page_label": "પા. …",
              "alt_book": "<optional>", "alt_section": <int> },
  "gloss": [ { "word": "…", "meaning": "…" } ],
  "meaning_en": "…", "why_en": "…", "reflect_en": "…"
}
```

Today's Pearl needs no maintenance — it rotates through all units by date.
