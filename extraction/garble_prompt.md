# Garble verification & repair — worker instructions

You verify pages of scanned Gujarati religious books against the printed page image and fix every transcription defect. A detector has flagged these pages; the flags are HINTS, not the full list — you must check the WHOLE page, not just flagged spots.

PDFs:
- samagam-purvardh → "/Users/harsh/RamKabir/Samagam - Full Content.pdf"
- samagam-uttarardh → "/Users/harsh/RamKabir/Samagam_Uttarardh_01_KiranRana_001.pdf"
- sant-darshan → "/Users/harsh/RamKabir/Sant Darshan.pdf"
- kirtan-gujarati → "/Users/harsh/RamKabir/ShreePadmanabhjiAdhyarujiKirtan_Gujarati.pdf"

Text lives at `/Users/harsh/RamKabir/extraction/<book>/txt-corrected/page-NNNN.txt` (create it from `txt/page-NNNN.txt` if absent). NNNN is the 4-digit page number you are given (it is the PDF page number too).

## For EACH assigned page

1. Render it: `pdftoppm -png -r 150 -f N -l N "<pdf>" <scratch>/pg` (zoom to 300–600 dpi crops for any word you are unsure of).
2. Read the rendered image AND the current text file.
3. Compare the ENTIRE page line by line. Fix every place the text disagrees with the print:
   - Latin garble standing in for Gujarati/Devanagari words (`HITMAN`, `FPL`, `TOHAS`, `wll`, `Yaa`, …)
   - malformed Gujarati/Devanagari (stray matras, dangling halants, wrong or dropped conjuncts, broken word splits)
   - dropped, duplicated, or out-of-order lines; detached column fragments to reattach
   - wrong verse/page numbers
4. Rules: the printed page is the ONLY authority. Preserve the print's own orthography, spelling quirks and typos. Never modernize, never paraphrase, never invent. Illegible → `[?]`. Lines that already match stay byte-identical.
5. **Genuine printed English** (the author's own English glosses, degrees like `M.A.`, `L.L.B.`, `Ph.D.`, publisher names, URLs, phone numbers, English words the book really prints) must be KEPT exactly. Record them: write `/Users/harsh/RamKabir/extraction/<book>/print_english/page-NNNN.json` containing a JSON array of the Latin tokens (length ≥2) that genuinely appear in the print on that page — `[]` if none. Create the directory if needed. This file is what stops the quality gate from flagging real English later, so it must list ONLY what you actually saw in the image.
6. Delete your rendered images as you go.

## Output
Final response: one line per page — `page-NNNN: <clean | fixed N | heavy>` and nothing else.
