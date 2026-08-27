#!/usr/bin/env python3
"""Assemble app/content/en/<book>.json from extraction/en/<book>/s<sec>-p<part>.json.

Enforces script purity: any Gujarati/Devanagari codepoint in an English field is
a hard error (reported, file skipped). Missing parts are reported loudly."""

import hashlib, json, re, sys
from pathlib import Path

BASE = Path(__file__).resolve().parents[1]

EXT = BASE / "extraction/en"
APP = BASE / "app/content"
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
            "src_sig": hashlib.sha1(re.sub(r"\s+", "", src_txt).encode("utf-8")).hexdigest()[:12],
            # NB: src_lines/src_order live in tools/provenance.json, not here —
            # they are tooling-only and were 4.4MB of payload for every reader
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
PROV = BASE / "tools/provenance.json"
prov = json.loads(PROV.read_text(encoding="utf-8")) if PROV.exists() else {}

# src_sig is the ONLY check that ties a translation to the exact source text it
# was made from. Recomputing it from whatever is in app/content today, and then
# overwriting provenance.json with fresh fingerprints, destroys that tie and the
# evidence needed to re-establish it — so a source section that changed after it
# was translated would silently look correct again. Re-stamping is the job of
# restamp_provenance.py, which only does it for a proven pure reorder.
drifted = []
for book, data in payloads.items():
    base = json.loads((APP / f"{book}.json").read_text(encoding="utf-8"))
    for i, sec in enumerate(json.loads(data)["sections"]):
        rec = prov.get(book, {}).get(str(i))
        if not sec or not rec:
            continue                      # never translated before: nothing to drift from
        src_txt = "\n".join(x["text"] for x in base["sections"][i]["blocks"])
        lines = [re.sub(r"\s+", "", l) for l in src_txt.split("\n") if l.strip()]
        now = hashlib.sha1("\n".join(sorted(lines)).encode("utf-8")).hexdigest()[:12]
        if rec.get("src_lines") != now:
            drifted.append(f"{book} #{i} '{base['sections'][i]['title'][:26]}'")
if drifted:
    print(f"SOURCE DRIFT ({len(drifted)}) — these sections changed since they were "
          f"translated, so a fresh signature would hide the change:")
    for d in drifted[:20]: print("  ", d)
    print("Re-translate them, or run tools/restamp_provenance.py --apply if the "
          "change is a pure reorder. NOTHING WRITTEN.")
    sys.exit(1)

for book, data in payloads.items():
    (OUT / f"{book}.json").write_text(data, encoding="utf-8")
    base = json.loads((APP / f"{book}.json").read_text(encoding="utf-8"))
    prov.setdefault(book, {})
    for i, sec in enumerate(json.loads(data)["sections"]):
        if not sec:
            continue
        src_txt = "\n".join(b["text"] for b in base["sections"][i]["blocks"])
        lines = [re.sub(r"\s+", "", l) for l in src_txt.split("\n") if l.strip()]
        prov[book][str(i)] = {
            "src_lines": hashlib.sha1("\n".join(sorted(lines)).encode("utf-8")).hexdigest()[:12],
            "src_order": lines,
        }
PROV.write_text(json.dumps(prov, ensure_ascii=False), encoding="utf-8")
# the integrity manifest covers app/content/**.json, including the English
# editions the builder never writes. Refreshing OUR entries here keeps the
# documented translation workflow from turning CI red and training someone
# into regenerating the whole manifest by hand.
MAN = BASE / "tools/integrity.json"
if MAN.exists():
    man = json.loads(MAN.read_text(encoding="utf-8"))
    for book in payloads:
        rel = f"en/{book}.json"
        man[rel] = hashlib.sha256((OUT / f"{book}.json").read_bytes()).hexdigest()[:16]
    MAN.write_text(json.dumps(man, indent=1), encoding="utf-8")
print(f"wrote {len(payloads)} English editions")
sys.exit(0)
