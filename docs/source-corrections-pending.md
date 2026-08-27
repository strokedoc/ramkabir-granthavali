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
| samagam-purvardh | 36 | `ભાગવત દર્શન-ભા. ૮૭-પા-૫૭` | `ભા. ૮૪-પા-પછ` | open |

Verified 2026-08-27 at 150/600dpi against `Samagam - Full Content.pdf` p.36.
The English edition for this section was corrected in the same pass and already
reads "Vol. 87, p. 57", so the two editions currently disagree.

## Standing risk

Digit and single-character OCR errors of this kind are invisible to every gate
we have. Only a page-by-page image comparison would find them all, which has not
been done for the ~1,300 Gujarati pages. Treat printed numbers (Samvat years,
volume/page citations, verse numbers) as the highest-risk class: three were
already found wrong in Sant Darshan (1712, 157, 129) and one here.
