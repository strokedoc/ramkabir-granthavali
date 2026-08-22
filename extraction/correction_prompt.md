# Image-grounded OCR correction — worker instructions

You are correcting tesseract OCR of scanned Gujarati devotional verse pages
(Shree Padmanabhji Adhyaruji na Kirtan, Ram Kabir sampraday). For EACH page N
in your assigned range:

1. Render: `pdftoppm -png -r 150 -f N -l N "/Users/harsh/RamKabir/ShreePadmanabhjiAdhyarujiKirtan_Gujarati.pdf" <your-scratch-dir>/pg`
2. Read the PNG and the raw OCR at
   `/Users/harsh/RamKabir/extraction/kirtan-gujarati/txt/page-NNNN.txt` (4-digit N).
3. Write the corrected full-page transcription to
   `/Users/harsh/RamKabir/extraction/kirtan-gujarati/txt-corrected/page-NNNN.txt`
4. Delete your rendered PNG before moving to the next page.

Correction rules — fidelity to the IMAGE is everything:
- Fix Latin garble (e.g. `del`→તહીં, `asl`→બૂડી, `arena`→સોભાગ્ય) and mangled
  digits/dandas (`willl`→॥૧॥) to exactly what the image shows.
- Tesseract often dumps the right-hand refrain column (સલૂણી / સોભાગ્ય / એ ॥N॥)
  as a detached list at the bottom — reattach refrains to their verse lines as
  printed, one printed line per output line.
- Preserve line breaks, verse numbers ॥૧૪॥, dandas, headers, printed page
  numbers like (૭૮), and printed typos (single danda where the book has one).
- NEVER guess a word the image doesn't support — write [?] if illegible.
  No translation, no spelling modernization, no additions.
- If a page is prose and the OCR is already correct, you may copy it with only
  the needed fixes — but only after actually comparing it to the image.
- Zoom (render at 300 dpi, or crop) when a word is ambiguous.

Final response: one line per page: `page-NNNN: <ok | fixed N issues | heavy reconstruction>`, nothing else.
