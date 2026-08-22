#!/bin/zsh
# Pages 177-365 of the kirtan volume may be Devanagari (Hindi sakhi work).
# OCR each page with guj+eng AND hin+eng, compare mean word confidence (TSV),
# keep the winner in txt/. Log decisions.
set -u
PDF="/Users/harsh/RamKabir/ShreePadmanabhjiAdhyarujiKirtan_Gujarati.pdf"
DIR="/Users/harsh/RamKabir/extraction/kirtan-gujarati"
WORK="$DIR/script-check"; mkdir -p "$WORK"
LOG="$DIR/script_report.txt"; : > "$LOG"

conf() { # mean confidence of real words in a tesseract TSV
  awk -F'\t' 'NR>1 && $11+0>0 && $12!="" {s+=$11; n++} END {print (n? s/n : 0)}' "$1"
}

for ((p=177; p<=365; p++)); do
  tag=$(printf "%04d" $p)
  pdftoppm -png -r 300 -f $p -l $p "$PDF" "$WORK/page" 2>/dev/null
  img=$(ls "$WORK"/page*.png | head -1)
  tesseract "$img" "$WORK/guj" -l guj+eng tsv 2>/dev/null
  tesseract "$img" "$WORK/hin" -l hin+eng tsv 2>/dev/null
  cg=$(conf "$WORK/guj.tsv"); ch=$(conf "$WORK/hin.tsv")
  if (( $(echo "$ch > $cg + 5" | bc -l) )); then
    tesseract "$img" "$DIR/txt/page-$tag" -l hin+eng 2>/dev/null
    echo "page-$tag: HIN (hin=$ch guj=$cg)" >> "$LOG"
  else
    echo "page-$tag: guj (hin=$ch guj=$cg)" >> "$LOG"
  fi
  rm -f "$WORK"/page*.png
done
echo "DONE $(grep -c HIN "$LOG") pages re-OCRed as Hindi" >> "$LOG"
tail -1 "$LOG"
