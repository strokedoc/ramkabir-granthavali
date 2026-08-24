# Garbled-line repair — worker instructions (image-grounded)

You repair OCR/extraction garble in Gujarati religious books. You receive a book id and page numbers. PDF paths:
- samagam-purvardh → "/Users/harsh/RamKabir/Samagam - Full Content.pdf"
- samagam-uttarardh → "/Users/harsh/RamKabir/Samagam_Uttarardh_01_KiranRana_001.pdf"
- sant-darshan → "/Users/harsh/RamKabir/Sant Darshan.pdf"
- kirtan-gujarati → "/Users/harsh/RamKabir/ShreePadmanabhjiAdhyarujiKirtan_Gujarati.pdf"

For EACH page N in your range:
1. Read the page text: prefer extraction/<book>/txt-corrected/page-NNNN.txt if it exists, else extraction/<book>/txt/page-NNNN.txt (under /Users/harsh/RamKabir/).
2. If the text contains NO [A-Za-z] characters, skip the page (do not rewrite it).
3. Otherwise render the page image (`pdftoppm -png -r 150 -f N -l N "<pdf>" <your-scratch>/pg`; zoom at 300+ dpi when unsure) and produce the corrected FULL page, writing it to extraction/<book>/txt-corrected/page-NNNN.txt.

Rules — the printed page is the only authority:
- Replace every Latin-garble token with exactly what the image shows (ગુજરાતી script; Devanagari where the print is Devanagari). Common garbles: "B."→છે., "al"/"wel"-type junk, run-together fragments, "II"/"|"→॥/।.
- Lines already correct stay VERBATIM — copy them unchanged; do not re-word, modernize spelling, or "improve" anything. Preserve the print's own orthography (છૂટચાં-style) and typos.
- Preserve line breaks, dandas, verse numbers, headings, printed folio numbers.
- Genuine printed Latin (rare: an English word or numeral in the print) may stay — only if the image shows Latin.
- Illegible → [?]. Never guess beyond the image.
- Delete pure junk lines only when the image shows nothing there (frame/photo artifacts).

Final response: one line per page — `page-NNNN: <skipped-clean | fixed N lines | heavy>` — nothing else.
