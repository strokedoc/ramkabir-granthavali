#!/usr/bin/env python3
"""Assemble app/content/en/<book>.json from extraction/en/<book>/s<sec>-p<part>.json.

Enforces script purity: any Gujarati/Devanagari codepoint in an English field is
a hard error (reported, file skipped). Missing parts are reported loudly."""

import hashlib, json, re, sys
from pathlib import Path

EXT = Path("/Users/harsh/RamKabir/extraction/en")
APP = Path("/Users/harsh/RamKabir/app/content")
OUT = APP / "en"
OUT.mkdir(parents=True, exist_ok=True)

IMPURE = re.compile(r"[ऀ-ॿ઀-૿]")
BOOKS = ["samagam-purvardh", "samagam-uttarardh", "sant-darshan", "kirtan-gujarati", "jivandas-sakhi"]

errors, missing, payloads = [], [], {}
for book in BOOKS:
    src_dir = EXT / book
    base = json.loads((APP / f"{book}.json").read_text(encoding="utf-8"))
    n_secs = len(base["sections"])
    sections = {}
    for f in sorted(src_dir.glob("s*-p*.json")) if src_dir.exists() else []:
        try:
            u = json.loads(f.read_text(encoding="utf-8"))
        except Exception as e:
            errors.append(f"{book}/{f.name}: unparseable ({e})")
            continue
        bad = [k for k in ("title_translit", "title_en", "translit", "translation")
               if IMPURE.search(u.get(k) or "")]
        if bad:
            errors.append(f"{book}/{f.name}: Gujarati/Devanagari chars in {bad}")
            continue
        sec = sections.setdefault(u["sec"], {"title_translit": "", "title_en": "", "parts": {}})
        if u.get("title_translit"):
            sec["title_translit"] = u["title_translit"]
            sec["title_en"] = u.get("title_en", "")
        sec["parts"][u["part"]] = {"translit": u.get("translit") or "", "translation": u.get("translation") or ""}
    out_secs = []
    for si in range(n_secs):
        if si not in sections:
            missing.append(f"{book} sec {si} ({base['sections'][si]['title'][:20]})")
            out_secs.append(None)
            continue
        sec = sections[si]
        parts = [sec["parts"][k] for k in sorted(sec["parts"])]
        src_txt = "\n".join(b["text"] for b in base["sections"][si]["blocks"])
        out_secs.append({
            # provenance: ties this translation to the exact source section it
            # was generated from, so a reorder/swap is detectable EXACTLY
            # rather than by fuzzy title or size heuristics
            "src_sig": hashlib.sha1(re.sub(r"\s+", "", src_txt)[:400].encode("utf-8")).hexdigest()[:12],
            "title_translit": sec["title_translit"],
            "title_en": sec["title_en"],
            "translit": "\n".join(p["translit"] for p in parts if p["translit"]).strip(),
            "translation": "\n\n".join(p["translation"] for p in parts if p["translation"]).strip(),
        })
    payloads[book] = json.dumps({"book": book, "sections": out_secs}, ensure_ascii=False)
    done = sum(1 for s in out_secs if s)
    print(f"{book}: {done}/{n_secs} sections assembled")

if errors:
    print(f"\nPURITY/PARSE ERRORS ({len(errors)}):")
    for e in errors: print("  ", e)
if missing:
    print(f"\nMISSING sections ({len(missing)}):")
    for m in missing[:30]: print("  ", m)
# An incomplete edition must never REACH app/content: a null section silently
# renders Gujarati text in English mode. Nothing is written unless every
# section of every book assembled cleanly.
if errors or missing:
    print("NOTHING WRITTEN — fix the reported problems and re-run")
    sys.exit(1)
for book, data in payloads.items():
    (OUT / f"{book}.json").write_text(data, encoding="utf-8")
print(f"wrote {len(payloads)} English editions")
sys.exit(0)
