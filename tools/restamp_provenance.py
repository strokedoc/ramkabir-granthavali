#!/usr/bin/env python3
"""Re-stamp English provenance signatures after a LEGITIMATE source change.

A repair that only reorders or re-whitespaces a source section leaves the
translation valid but invalidates its src_sig. Re-stamping is allowed ONLY when
the section's character multiset is unchanged (i.e. nothing was added, removed
or substituted). Any real edit must go back through re-translation instead.

Usage: python3 tools/restamp_provenance.py            # report what would change
       python3 tools/restamp_provenance.py --apply    # re-stamp the safe ones
"""
import hashlib, json, os, re, sys
from collections import Counter
from pathlib import Path

APP = Path("/Users/harsh/RamKabir/app/content")
PROV = Path("/Users/harsh/RamKabir/tools/provenance.json")
prov = json.loads(PROV.read_text(encoding="utf-8")) if PROV.exists() else {}
ORNAMENT = re.compile(r"[=~_*·•\-]{3,}")
INDIC_LETTER = re.compile(r"[ઁ-૏ऀ-ॏॐ-ॣॱ-ॿ]")
# SRC_DIR lets this compare against a STAGED build (the new source) while still
# writing the English editions in their real location
SRC = Path(os.environ.get("SRC_DIR") or APP)
BOOKS = ["samagam-purvardh", "samagam-uttarardh", "sant-darshan",
         "kirtan-gujarati", "jivandas-sakhi"]
apply = "--apply" in sys.argv
safe = unsafe = 0

for b in BOOKS:
    gu = json.loads((SRC / f"{b}.json").read_text(encoding="utf-8"))
    f = APP / "en" / f"{b}.json"
    en = json.loads(f.read_text(encoding="utf-8"))
    changed = False
    for i, es in enumerate(en["sections"]):
        if not es or i >= len(gu["sections"]):
            continue
        src = "\n".join(x["text"] for x in gu["sections"][i]["blocks"])
        norm = re.sub(r"\s+", "", src)
        want = hashlib.sha1(norm.encode("utf-8")).hexdigest()[:12]
        if es.get("src_sig") == want:
            continue
        lines = [re.sub(r"\s+", "", l) for l in src.split("\n") if l.strip()]
        now_lines = hashlib.sha1("\n".join(sorted(lines)).encode("utf-8")).hexdigest()[:12]
        rec = prov.get(b, {}).get(str(i), {})
        prev_lines = rec.get("src_lines")
        moved = rec.get("src_order")
        # SAFE only when: the set of lines is unchanged (nothing added, removed
        # or substituted) AND at most a few lines changed position. Without a
        # recorded fingerprint we cannot prove either, so it is NOT safe.
        # Only ORNAMENT/heading lines may have moved. Allowing "a few" moves
        # accepted a verse swap (exactly two positional changes) while the
        # translation kept the old reading order.
        small_move = True
        if moved:
            before = [l for l in moved if l in set(lines)]
            after = [l for l in lines if l in set(moved)]
            shifted = {a_ for a_, b_ in zip(before, after) if a_ != b_} | \
                      {b_ for a_, b_ in zip(before, after) if a_ != b_}
            small_move = all(ORNAMENT.search(x) and not INDIC_LETTER.search(x)
                             for x in shifted)
        if prev_lines is not None and prev_lines == now_lines and small_move:
            print(f"  SAFE  {b} #{i} '{gu['sections'][i]['title'][:26]}' (reorder only)")
            es["src_sig"] = want
            prov.setdefault(b, {})[str(i)] = {"src_lines": now_lines, "src_order": lines}
            safe += 1
            changed = True
        elif prev_lines is None:
            print(f"  UNSAFE {b} #{i} '{gu['sections'][i]['title'][:26]}' — no recorded "
                  f"fingerprint; cannot prove the change was a reorder")
            unsafe += 1
        else:
            print(f"  UNSAFE {b} #{i} '{gu['sections'][i]['title'][:26]}' — content changed; "
                  f"re-translate rather than re-stamp")
            unsafe += 1
    if changed and apply:
        f.write_text(json.dumps(en, ensure_ascii=False), encoding="utf-8")
        PROV.write_text(json.dumps(prov, ensure_ascii=False), encoding="utf-8")

print(f"{safe} safe to re-stamp, {unsafe} require re-translation"
      + ("" if apply else "  (dry run — pass --apply to write)"))
sys.exit(1 if unsafe else 0)
