#!/bin/zsh
# OCR pipeline: render each PDF page at 300dpi, tesseract Gujarati+English OCR.
# Output: extraction/<book>/txt/page-NNNN.txt  (images deleted after OCR to save disk)
set -u
BASE="/Users/harsh/RamKabir"
OUT="$BASE/extraction"

ocr_book() {
  local pdf="$1" slug="$2" pages="$3"
  local dir="$OUT/$slug"
  mkdir -p "$dir/txt" "$dir/img"
  echo "=== $slug ($pages pages) start $(date +%H:%M:%S)"
  for ((p=1; p<=pages; p++)); do
    local tag=$(printf "%04d" $p)
    [[ -s "$dir/txt/page-$tag.txt" ]] && continue  # resumable
    pdftoppm -png -r 300 -f $p -l $p "$pdf" "$dir/img/page-$tag" 2>/dev/null
    local img=$(ls "$dir/img/page-$tag"*.png 2>/dev/null | head -1)
    if [[ -n "$img" ]]; then
      tesseract "$img" "$dir/txt/page-$tag" -l guj+eng 2>/dev/null
      rm -f "$img"
    else
      echo "(render failed p$p)" > "$dir/txt/page-$tag.txt"
    fi
  done
  echo "=== $slug done $(date +%H:%M:%S)  chars: $(cat "$dir/txt/"*.txt | wc -c)"
}

ocr_book "$BASE/Samagam - Full Content.pdf"                     samagam-purvardh 358
ocr_book "$BASE/Samagam_Uttarardh_01_KiranRana_001.pdf"         samagam-uttarardh 403
ocr_book "$BASE/Sant Darshan.pdf"                               sant-darshan 176
ocr_book "$BASE/ShreePadmanabhjiAdhyarujiKirtan_Gujarati.pdf"   kirtan-gujarati 365
echo "ALL DONE $(date)"
