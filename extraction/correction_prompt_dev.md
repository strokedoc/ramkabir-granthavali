# Image-grounded OCR correction — Devanagari volume (worker instructions)

Same task as correction_prompt.md but for the વૈષ્ણવ જીવણદાસજીકી સાખી portion
of the volume, which is printed mostly in DEVANAGARI (Hindi/Vraj sakhis), with
occasional Gujarati-script pages (front matter, some headings) and Gujarati
numerals inside dandas (॥૧॥).

For EACH page N in your assigned range:
1. Render: `pdftoppm -png -r 150 -f N -l N "/Users/harsh/RamKabir/ShreePadmanabhjiAdhyarujiKirtan_Gujarati.pdf" <your-scratch-dir>/pg`
2. Read the PNG and the raw OCR at
   `/Users/harsh/RamKabir/extraction/kirtan-gujarati/txt/page-NNNN.txt` (4-digit N).
3. Write the corrected full-page transcription to
   `/Users/harsh/RamKabir/extraction/kirtan-gujarati/txt-corrected/page-NNNN.txt`
4. Delete the PNG before the next page.

Rules — fidelity to the IMAGE is everything:
- Transcribe in the script the page is PRINTED in (Devanagari stays Devanagari,
  Gujarati stays Gujarati — never convert between scripts).
- Fix Latin garble (`fax`, `ad`, `Waa`, `I!` for ॥) and mangled digits to what
  the image shows; keep Gujarati numerals if that's what is printed (॥૧॥).
- Sakhi couplets print as two half-lines separated by a danda — keep one
  printed line per output line; reattach any column tesseract detached.
- Preserve headings (॥ साखी ॥, अंग titles), printed page numbers like (१८८),
  and printed typos. Never guess an illegible word — write [?].
- No translation, no spelling modernization, no additions.
- Zoom (300 dpi render or crop) when ambiguous.

Final response: one line per page: `page-NNNN: <ok | fixed N issues | heavy reconstruction>`, nothing else.
