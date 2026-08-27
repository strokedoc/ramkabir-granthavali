# Source-level OCR errors found during the image-grounded English repair

These are errors in the GUJARATI corpus (extraction/*/txt-corrected/), not in the
English edition. They survived OCR correction because they are well-formed
Gujarati characters — the garble detector looks for Latin letters and malformed
Indic, and a wrong-but-valid digit passes it cleanly.

Fixing one changes the corpus, which invalidates the `src_sig` of the English
section built from it, so each fix must be paired with a re-verified translation
for that section (which the repair pass has already produced).

| Book | Page | Printed (verified on image) | In txt-corrected | Status |
|---|---|---|---|---|
| samagam-purvardh | 36 | `ભાગવત દર્શન-ભા. ૮૭-પા-૫૭` | `ભા. ૮૪-પા-પછ` | FIXED |
| samagam-uttarardh | 215 | `લીટિંયું ૯૨ પા. ૧૦૫` | `લીટિંયું લર પા. ૧૦૫` | FIXED |
| samagam-uttarardh | 187 | `સદોષ ક્રિયા` | `સદોષ ક્યા` | FIXED |

All three verified by me at 600dpi before the corpus was touched. The ૯૨/લર
case is the instructive one: Gujarati ૨ and ર are near-identical glyphs, so a
citation number read as a letter pair is well-formed text that no gate can
question. Each correction was paired with its already-re-verified translation
through `restamp_provenance.py --source-fixed`, which names the exact sections
and prints each one — the guard is never bypassed, only answered explicitly.

## Cosmetic, left as-is

Outside the printed English volume the Gujarati corpus contains 32 runs of
ASCII digits: decorative separators (`====0000====`), the printer's phone
number on a credits page, a contents list numbered `(3)`…`(10)`, and two
citations (`ખંડ 32`, and `300` inside a Devanagari line). The VALUES are
correct; only the script differs. Not worth changing the corpus for.

Verified 2026-08-27 at 150/600dpi against `Samagam - Full Content.pdf` p.36.
The English edition for this section was corrected in the same pass and already
reads "Vol. 87, p. 57", so the two editions currently disagree.

## Standing risk

Digit and single-character OCR errors of this kind are invisible to every gate
we have. Only a page-by-page image comparison would find them all, which has not
been done for the ~1,300 Gujarati pages. Treat printed numbers (Samvat years,
volume/page citations, verse numbers) as the highest-risk class: three were
already found wrong in Sant Darshan (1712, 157, 129) and one here.

## Errors in the PRINTED BOOKS, faithfully reproduced (do not "fix")

These are the books' own mistakes. The corpus reproduces them on purpose; a
later pass that "corrects" them would be departing from the source.

| Book | Page | What the book prints | Note |
|---|---|---|---|
| samagam-purvardh | 22 | `Amaigamation Combination` | the print's own typo for "Amalgamation"; verified at 600dpi |
| kirtan-gujarati | 15 | `૧૬૬૪` | the sense requires 1964; the English notes the discrepancy rather than silently fixing it |
| jivandas-sakhi | 361 | doha numbered `૧૬૩` where `૧૬૧` belongs | numbering runs …160, 163, 162, 163, 164…; the print itself is wrong |

## Verification coverage so far

Image-by-image comparison of source text against the scans has been done for
the pages touched by the English repair pass, not the whole corpus:

- kirtan-gujarati: 33 pages compared digit by digit — **no discrepancies**, and
  verse numbering re-checked across all 38 sections.
- jivandas-sakhi: 26 pages compared — **no discrepancies**; doha numbering
  checked mechanically across all 26 sections (the one anomaly is the print's).
- samagam-purvardh: the one error above.
- sant-darshan: three wrong numbers found and fixed in the ENGLISH (1712, 157,
  129); the Gujarati was not systematically digit-checked.

So the corpus looks sound rather than systematically corrupt, but coverage is
partial and concentrated on pages that happened to need translation repair.
