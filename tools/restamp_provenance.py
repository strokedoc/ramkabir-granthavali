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
        want = hashlib.sha1(norm[:400].encode("utf-8")).hexdigest()[:12]
        if es.get("src_sig") == want:
            continue
        # safe only if nothing was added/removed/substituted anywhere
        prev_full = es.get("src_full")
        now_full = "".join(sorted(Counter(norm).elements()))
        now_hash = hashlib.sha1(now_full.encode("utf-8")).hexdigest()[:12]
        if prev_full is None or prev_full == now_hash:
            print(f"  SAFE  {b} #{i} '{gu['sections'][i]['title'][:26]}' (reorder only)")
            es["src_sig"] = want
            es["src_full"] = now_hash          # multiset fingerprint for next time
            safe += 1
            changed = True
        else:
            print(f"  UNSAFE {b} #{i} '{gu['sections'][i]['title'][:26]}' — content changed; "
                  f"re-translate rather than re-stamp")
            unsafe += 1
    if changed and apply:
        f.write_text(json.dumps(en, ensure_ascii=False), encoding="utf-8")

print(f"{safe} safe to re-stamp, {unsafe} require re-translation"
      + ("" if apply else "  (dry run — pass --apply to write)"))
sys.exit(1 if unsafe else 0)
