/* ॥ રામકબીર ગ્રંથાવલિ ॥
   Static PWA: hash routing, JSON content, cross-script search, localStorage state.
   No framework, no build step. */

"use strict";

const $ = (sel, el = document) => el.querySelector(sel);
const view = $("#view");

/* ---------------- state ---------------- */
const store = {
  get(key, fallback) {
    try { const v = localStorage.getItem(key); return v === null ? fallback : JSON.parse(v); }
    catch { return fallback; }
  },
  set(key, val) { try { localStorage.setItem(key, JSON.stringify(val)); } catch {} },
};

let manifest = null;            // books.json -> books array
let featured = [];              // pinned quick-access items
const bookCache = {};           // id -> book json
let searchIndex = null;         // built lazily

/* ---------------- language (gu / en) ---------------- */
const STR = {
  appTitle:   { gu: "રામકબીર ગ્રંથાવલિ", en: "Ramkabir Granthavali" },
  navBooks:   { gu: "ગ્રંથો", en: "Books" },
  navSaar:    { gu: "સાર", en: "Essence" },
  navSearch:  { gu: "શોધ", en: "Search" },
  navMarks:   { gu: "નિશાની", en: "Marks" },
  continueL:  { gu: "વાંચન ચાલુ રાખો", en: "Continue reading" },
  sections:   { gu: "વિભાગ", en: "sections" },
  pagesW:     { gu: "પાનાં", en: "pages" },
  compositions: { gu: "રચનાઓ", en: "compositions" },
  invocation: { gu: "રામકબીર સંપ્રદાય", en: "Ram Kabir Sampraday" },
  pageAbbr:   { gu: "પા.", en: "p." },
  pearlLabel: { gu: "આજનું મોતી", en: "Today's Pearl" },
  pearls:     { gu: "મોતી", en: "pearls" },
  bmOn:       { gu: "✓ નિશાની છે", en: "✓ Bookmarked" },
  bmOff:      { gu: "✻ નિશાની કરો", en: "✻ Bookmark this" },
  bmEmpty:    { gu: "હજી કોઈ નિશાની નથી.<br>વાંચતી વખતે \"નિશાની કરો\" દબાવો.", en: "No bookmarks yet.<br>Tap \"Bookmark this\" while reading." },
  searchPh:   { gu: "શોધો… ganpati / હરિ / kirtan", en: "Search… ganpati / hari / kirtan" },
  searchHint: { gu: "ગુજરાતી અથવા અંગ્રેજી અક્ષરે લખો — બન્ને ચાલશે.", en: "Type in English or Gujarati letters — both work." },
  searching:  { gu: "શોધી રહ્યા છીએ…", en: "Searching…" },
  noResults:  { gu: "કંઈ મળ્યું નહિ.", en: "Nothing found." },
  moreResults:{ gu: "પરિણામ — વધુ ચોક્કસ શોધો.", en: "results — try a narrower search." },
  readInBook: { gu: "ગ્રંથમાં વાંચો →", en: "Read in the book →" },
  gloss:      { gu: "શબ્દાર્થ", en: "WORD MEANINGS" },
  meaning:    { gu: "ભાવાર્થ", en: "MEANING" },
  why:        { gu: "કેમ મહત્વનું", en: "WHY IT MATTERS" },
  searchTitle:{ gu: "શોધ", en: "Search" },
  marksTitle: { gu: "નિશાની", en: "Bookmarks" },
  saarTitle:  { gu: "સાર", en: "Essence" },
  toEnglish:  { gu: "આ કીર્તન અંગ્રેજીમાં →", en: "This kirtan in English →" },
  toGujarati: { gu: "આ કીર્તન ગુજરાતીમાં →", en: "This kirtan in Gujarati →" },
  loadFail:   { gu: "સામગ્રી લોડ ન થઈ.", en: "Content failed to load." },
  searchCleared: { gu: "શોધ ખાલી કરી", en: "Search cleared" },
  results:    { gu: "પરિણામ", en: "results" },
  // control labels announced by screen readers
  a11yBack:   { gu: "પાછળ", en: "Back" },
  a11ySmaller:{ gu: "નાના અક્ષર", en: "Smaller text" },
  a11yLarger: { gu: "મોટા અક્ષર", en: "Larger text" },
  a11yLang:   { gu: "ભાષા બદલો — English", en: "Change language — ગુજરાતી" },
  a11yTheme:  { gu: "થીમ બદલો", en: "Change theme" },
  a11yNav:    { gu: "મુખ્ય", en: "Main" },
};
let lang = store.get("lang", "gu");
function t(key) { return (STR[key] || {})[lang] || (STR[key] || {}).gu || key; }
function applyLang() {
  document.documentElement.lang = lang;
  document.title = t("appTitle");
  const aria = {
    "#back-btn": "a11yBack", "#font-minus": "a11ySmaller", "#font-plus": "a11yLarger",
    "#lang-btn": "a11yLang", "#theme-btn": "a11yTheme", "#bottomnav": "a11yNav",
  };
  for (const [sel, key] of Object.entries(aria)) {
    const el = $(sel);
    if (el) el.setAttribute("aria-label", t(key));
  }
  const btn = $("#lang-btn");
  if (btn) btn.textContent = lang === "gu" ? "EN" : "ગુ";
  document.querySelectorAll("#topbar-title .ornament").forEach(o => {
    o.textContent = lang === "en" ? "||" : "॥";
  });
  document.querySelectorAll("#bottomnav a").forEach(a => {
    const key = { library: "navBooks", saar: "navSaar", search: "navSearch", bookmarks: "navMarks" }[a.dataset.nav];
    a.querySelector("span:last-child").textContent = t(key);
  });
}
/* book title helpers: primary/secondary by language */
function bt(b) { return lang === "en" ? b.title_en : b.title_gu; }
function bts(b) { return lang === "en" ? b.title_gu : b.title_en; }

/* Gujarati kirtan sections 1..31 ↔ English volume sections 0..30 */
function crossLink(bookId, idx) {
  if (bookId === "kirtan-gujarati" && idx >= 1 && idx <= 31)
    return { book: "kirtan-english", section: idx - 1, label: t("toEnglish"), lang: "en" };
  if (bookId === "kirtan-english" && idx <= 30)
    return { book: "kirtan-gujarati", section: idx + 1, label: t("toGujarati"), lang: "gu" };
  return null;
}
/* "#/book/<id>/<section>/<lang>" — the language travels WITH the URL so the
   link behaves correctly in a new tab, on middle-click, and when bookmarked */
function bookHref(book, section, forceLang) {
  return `#/book/${book}/${section}` + (forceLang ? `/${forceLang}` : "");
}

/* ---------------- theme & font size ---------------- */
function applyTheme() {
  const t = store.get("theme", null); // null = follow system
  if (t) document.documentElement.setAttribute("data-theme", t);
  else document.documentElement.removeAttribute("data-theme");
}
function systemDark() { return matchMedia("(prefers-color-scheme: dark)").matches; }
$("#theme-btn").addEventListener("click", () => {
  const cur = store.get("theme", null) || (systemDark() ? "dark" : "light");
  store.set("theme", cur === "dark" ? "light" : "dark");
  applyTheme();
});
if (systemDark() && !store.get("theme", null)) document.documentElement.setAttribute("data-theme", "dark");
applyTheme();
$("#lang-btn").addEventListener("click", () => {
  rememberScroll();          // a language switch re-routes without a hashchange
  lang = lang === "gu" ? "en" : "gu";
  store.set("lang", lang);
  applyLang();
  const p = parseHash();
  if (p[0] === "book" && p.length >= 4) {     // never let a URL segment win
    // keep eid/y: dropping them orphans this entry's saved reading position
    history.replaceState({ ...(history.state || {}), lang, eid: entryId }, "",
      location.pathname + location.search + "#/" + p.slice(0, 3).join("/"));
    prevHash = location.hash;
  } else {
    history.replaceState({ ...(history.state || {}), lang, eid: entryId }, "", location.href);
  }
  route();
});
applyLang();

function applyFontScale() {
  document.documentElement.style.setProperty("--gu-size", store.get("fontScale", 1));
}
$("#font-plus").addEventListener("click", () => bumpFont(+0.1));
$("#font-minus").addEventListener("click", () => bumpFont(-0.1));
function bumpFont(d) {
  const s = Math.min(1.8, Math.max(0.7, +(store.get("fontScale", 1) + d).toFixed(2)));
  store.set("fontScale", s); applyFontScale();
  if (pagerState) pagerState.relayout();
}
applyFontScale();

/* ---------------- transliteration (lossy, consistent) ----------------
   One normalize() used for indexed text AND queries, so Gujarati script,
   roman transliteration, and sloppy roman typing all meet in the middle. */
const GU = {
  "ક":"k","ખ":"kh","ગ":"g","ઘ":"gh","ઙ":"n","ચ":"ch","છ":"chh","જ":"j","ઝ":"jh","ઞ":"n",
  "ટ":"t","ઠ":"th","ડ":"d","ઢ":"dh","ણ":"n","ત":"t","થ":"th","દ":"d","ધ":"dh","ન":"n",
  "પ":"p","ફ":"ph","બ":"b","ભ":"bh","મ":"m","ય":"y","ર":"r","લ":"l","વ":"v","ળ":"l",
  "શ":"sh","ષ":"sh","સ":"s","હ":"h",
  "અ":"a","આ":"a","ઇ":"i","ઈ":"i","ઉ":"u","ઊ":"u","ઋ":"ru","એ":"e","ઐ":"ai","ઓ":"o","ઔ":"au",
  "ા":"a","િ":"i","ી":"i","ુ":"u","ૂ":"u","ૃ":"ru","ે":"e","ૈ":"ai","ો":"o","ૌ":"au",
  "ં":"n","ઃ":"","ઁ":"n","્":"",
  "૦":"0","૧":"1","૨":"2","૩":"3","૪":"4","૫":"5","૬":"6","૭":"7","૮":"8","૯":"9",
};
/* Devanagari (the sakhi volume is printed in Hindi) — same skeleton. */
const DEV = {
  "क":"k","ख":"kh","ग":"g","घ":"gh","ङ":"n","च":"ch","छ":"chh","ज":"j","झ":"jh","ञ":"n",
  "ट":"t","ठ":"th","ड":"d","ढ":"dh","ण":"n","त":"t","थ":"th","द":"d","ध":"dh","न":"n",
  "प":"p","फ":"ph","ब":"b","भ":"bh","म":"m","य":"y","र":"r","ल":"l","व":"v","ळ":"l",
  "श":"sh","ष":"sh","स":"s","ह":"h",
  "अ":"a","आ":"a","इ":"i","ई":"i","उ":"u","ऊ":"u","ऋ":"ru","ए":"e","ऐ":"ai","ओ":"o","औ":"au",
  "ा":"a","ि":"i","ी":"i","ु":"u","ू":"u","ृ":"ru","े":"e","ै":"ai","ो":"o","ौ":"au",
  "ं":"n","ः":"","ँ":"n","्":"",
  "०":"0","१":"1","२":"2","३":"3","४":"4","५":"5","६":"6","७":"7","८":"8","९":"9",
};
function translit(str) {
  let out = "";
  for (const ch of str) out += (GU[ch] ?? DEV[ch] ?? ch);
  return out;
}
/* Collapse to a fuzzy skeleton: lowercase, transliterate, drop 'a' (inherent
   vowel — "ganapati" and "ganpati" both become "gnpti"), squeeze h-clusters
   so th/t, dh/d, sh/s match, drop punctuation. */
function normalize(str) {
  return translit(str.toLowerCase())
    .replace(/[^a-z0-9\s]/g, " ")
    .replace(/([kgcjtdpbs])h/g, "$1")
    .replace(/chh|ch/g, "c")
    .replace(/a/g, "")
    .replace(/\s+/g, " ")
    .trim();
}

/* ---------------- data loading ---------------- */
async function loadManifest() {
  if (!manifest) {
    const data = await (await fetch("content/books.json")).json();
    manifest = data.books;
    featured = data.featured || [];
  }
  return manifest;
}
/* cache the in-flight PROMISE, so two rapid navigations share one request
   instead of racing each other */
function loadBook(id) {
  if (!bookCache[id]) {
    bookCache[id] = fetch(`content/${id}.json`).then(r => r.json())
      .catch(err => { delete bookCache[id]; throw err; });
  }
  return bookCache[id];
}
const enCache = {};
function loadEn(id) {
  if (!(id in enCache)) {
    enCache[id] = fetch(`content/en/${id}.json`).then(r => r.json()).catch(() => null);
  }
  return enCache[id];
}
function enSec(en, idx) { return (en && en.sections && en.sections[idx]) || null; }
/* predominantly-Devanagari text needs the Devanagari face first, otherwise the
   Gujarati subset claims its dandas (। ॥) and the punctuation mismatches */
function devClass(text) {
  const d = (text.match(/[\u0900-\u094f\u0958-\u097f]/g) || []).length;
  const g = (text.match(/[\u0a80-\u0aff]/g) || []).length;
  return d > g ? " dev" : "";
}
function secTitle(book, en, idx) {
  const s = book.sections[idx];
  if (lang !== "en") return s.title;
  const e = enSec(en, idx);
  return (e && e.title_translit) || s.title;
}

let teachings = null;
async function loadTeachings() {
  if (!teachings) {
    teachings = await (await fetch("content/teachings.json")).json();
    try {
      const gu = await (await fetch("content/teachings-gu.json")).json();
      Object.assign(teachings.story, gu.story);
      teachings.themes.forEach(th => {
        th.intro_gu = (gu.intros || {})[th.id] || "";
        th.units.forEach(u => Object.assign(u, (gu.units || {})[u.id] || {}));
      });
    } catch {}
  }
  return teachings;
}
/* language-sensitive field pickers for સાર */
function uf(u, base) { return lang === "en" ? u[base + "_en"] : (u[base + "_gu"] || u[base + "_en"]); }
const GU_DIGITS = { "૦":"0","૧":"1","૨":"2","૩":"3","૪":"4","૫":"5","૬":"6","૭":"7","૮":"8","૯":"9" };
function pageLabel(src) {
  if (lang === "en") return src.page_label_en || (src.page_label || "").replace(/[૦-૯]/g, d => GU_DIGITS[d]).replace(/પા\./g, "p.");
  return src.page_label || "";
}
function allUnits(t) {
  const out = [];
  t.themes.forEach((th, ti) => th.units.forEach((u, ui) => out.push({ th, ti, u, ui })));
  return out;
}
function todaysPearl(t) {
  const units = allUnits(t);
  const day = Math.floor(Date.now() / 86400000);
  return units[day % units.length];
}

/* ---------------- routing ---------------- */
// take over scroll restoration: the browser's automatic restore runs AFTER our
// own and would re-apply the previous section's offset to a new destination
if ("scrollRestoration" in history) history.scrollRestoration = "manual";
const scrollPositions = (() => {
  try { return JSON.parse(sessionStorage.getItem("scrollPos") || "{}"); }
  catch { return {}; }
})();
let prevHash = location.hash;
let prevKey = null;                  // set once the first entry has an id
const SCROLL_MAX = 40;      // bounded: search hashes carry arbitrary queries
function persistScroll() {
  const keep = scrollKey();          // the current destination is never evicted
  const keys = Object.keys(scrollPositions).filter(k => k !== keep);
  for (const k of keys.slice(0, Math.max(0, keys.length - SCROLL_MAX))) delete scrollPositions[k];
  try {
    sessionStorage.setItem("scrollPos", JSON.stringify(scrollPositions));
  } catch {
    // quota exhausted: drop history rather than silently stop persisting
    for (const k of Object.keys(scrollPositions).slice(0, keys.length - 5)) delete scrollPositions[k];
    try { sessionStorage.setItem("scrollPos", JSON.stringify(scrollPositions)); } catch {}
  }
}
let entryId = null;
function ensureEntryId() {
  const st = history.state || {};
  if (!st.eid) {
    entryId = "e" + Date.now().toString(36) + Math.random().toString(36).slice(2, 6);
    history.replaceState({ ...st, eid: entryId, lang }, "", location.href);
  } else {
    entryId = st.eid;
  }
  return entryId;
}
function scrollKey() { return (entryId || "") + "|" + location.hash; }
// stamp the initial history entry so even the first screen's position is keyed
ensureEntryId();
prevKey = scrollKey();
function rememberScroll() {
  // also stamp the position into the history entry: sessionStorage can be
  // denied (private browsing), but history.state survives a reload
  try { history.replaceState({ ...(history.state || {}), y: scrollY }, "", location.href); } catch {}
  const k = scrollKey();
  delete scrollPositions[k];                 // re-insert so the cap is LRU, not FIFO
  scrollPositions[k] = scrollY;
  persistScroll();
}
addEventListener("pagehide", rememberScroll);
addEventListener("visibilitychange", () => { if (document.hidden) rememberScroll(); });
function restoreScroll() {
  // Back/Forward returns to where the reader left off; a fresh destination
  // starts at the top
  const st = history.state || {};
  const y = scrollPositions[scrollKey()] ?? (st.eid === entryId ? st.y || 0 : 0);
  // scroll immediately, then once more after layout settles. NOT via
  // requestAnimationFrame alone: rAF never fires while the tab is hidden,
  // which would leave a new section showing the previous one's scroll offset.
  window.scrollTo(0, y);
  setTimeout(() => window.scrollTo(0, y), 0);
}
addEventListener("hashchange", () => {
  // record where we LEFT, keyed by the hash we are leaving — sampling during
  // navigation would stamp the old position onto the new destination
  delete scrollPositions[prevHash];
  if (prevKey) scrollPositions[prevKey] = scrollY;
  // NOT stamped into history.state here: by hashchange time the new entry is
  // already current, so this would write the position we are LEAVING onto the
  // destination. pagehide/visibilitychange stamp the correct entry.
  persistScroll();
  ensureEntryId();
  prevKey = scrollKey();
  prevHash = location.hash;
  route();
});
window.addEventListener("DOMContentLoaded", route);

function parseHash() {
  const h = location.hash.replace(/^#\/?/, "");
  return h.split("/").filter(Boolean);
}

/* every route() run gets a token; an async renderer that finishes after a
   newer navigation started must not paint over the newer screen */
let routeToken = 0;
function stale(tok) { return tok !== routeToken; }

async function route() {
  const tok = ++routeToken;
  if (pagerState) { pagerState.dispose(); pagerState = null; }
  clearTimeout(searchTimer);     // a detached debounce must not rewrite the
  searchGen++;                     // address or query a screen that is gone
  const parts = parseHash();
  // "#/book/<id>/<sec>/<lang>" carries the language with the link
  ensureEntryId();
  if (parts[0] === "book" && parts.length >= 4 && (parts[3] === "en" || parts[3] === "gu")) {
    if (lang !== parts[3]) { lang = parts[3]; store.set("lang", lang); applyLang(); }
    parts.length = 3;
    // drop the segment so the toggle is not locked and Back is not re-pinned
    const clean = "#/" + parts.join("/");
    history.replaceState({ lang, eid: entryId }, "", location.pathname + location.search + clean);
    prevHash = clean; prevKey = scrollKey();
  } else if (history.state && history.state.lang && history.state.lang !== lang) {
    // Back/Forward returns to an entry that was viewed in the other language
    lang = history.state.lang; store.set("lang", lang); applyLang();
  } else {
    history.replaceState({ ...(history.state || {}), lang, eid: entryId }, "", location.href);
  }
  const navKey = parts[0] === "search" ? "search" : parts[0] === "bookmarks" ? "bookmarks"
    : parts[0] === "saar" ? "saar" : "library";
  document.querySelectorAll("#bottomnav a").forEach(a => {
    const on = a.dataset.nav === navKey;
    a.classList.toggle("active", on);
    if (on) a.setAttribute("aria-current", "page"); else a.removeAttribute("aria-current");
  });

  const readerMode = parts[0] === "book" && parts.length >= 3;
  view.classList.toggle("reading", readerMode);
  $("#font-plus").hidden = $("#font-minus").hidden = !readerMode;
  $("#back-btn").hidden = parts.length === 0;

  // one place guarantees the scroll reset for EVERY route, including the
  // early-return paths inside individual renderers
  const done = async (p) => { const v = await p; if (!stale(tok)) restoreScroll(); return v; };
  try {
    if (parts.length === 0) return await done(renderLibrary(tok));
    if (parts[0] === "search") return await done(renderSearch(decodeURIComponent(parts[1] || ""), tok));
    if (parts[0] === "bookmarks") return await done(renderBookmarks(tok));
    if (parts[0] === "saar" && parts[1] === "story") return await done(renderStory(tok));
    if (parts[0] === "saar" && parts.length === 3) return await done(renderUnit(+parts[1], +parts[2], tok));
    if (parts[0] === "saar" && parts.length === 2) return await done(renderTheme(+parts[1], tok));
    if (parts[0] === "saar") return await done(renderSaar(tok));
    if (parts[0] === "book" && parts.length === 2) return await done(renderToc(parts[1], tok));
    if (parts[0] === "book" && parts.length >= 3) return await done(renderReader(parts[1], parseInt(parts[2], 10), tok));
    return await done(renderLibrary(tok));
  } catch (err) {
    if (stale(tok)) return;
    view.innerHTML = `<div class="empty"><span class="glyph">✻</span>
      ${escapeHtml(t("loadFail"))} ${escapeHtml(String(err.message || err))}</div>`;
  }
}
$("#back-btn").addEventListener("click", () => {
  const parts = parseHash();
  if (parts[0] === "book" && parts.length >= 3) location.hash = `#/book/${parts[1]}`;
  else if (parts[0] === "saar" && parts.length === 3) location.hash = `#/saar/${parts[1]}`;
  else if (parts[0] === "saar" && parts.length === 2) location.hash = "#/saar";
  else location.hash = "#/";
});

function setTitle(text, opts = {}) {
  $("#topbar-text").textContent = text;
  // announce the destination to assistive tech and reset the reading position
  document.title = text === t("appTitle") ? text : `${text} · ${t("appTitle")}`;
  if (!opts.keepFocus) view.focus({ preventScroll: true });
}
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
}

/* ---------------- library ---------------- */
async function renderLibrary(tok) {
  setTitle(t("appTitle"));
  const books = await loadManifest();
  const last = store.get("lastRead", null);
  let tj = null;
  try { tj = await loadTeachings(); } catch {}
  let html = `<div class="reveal">
    <div class="hero">
      <div class="invocation">${escapeHtml(t("invocation"))}</div>
      <h2>${lang === "en" ? "" : "॥ "}${escapeHtml(t("appTitle"))}${lang === "en" ? "" : " ॥"}</h2>
      <hr class="rule">
    </div>`;
  if (tj) html += pearlCard(tj);
  const visible = books.filter(b => b.language !== "translit" || lang === "en");
  const visibleIds = new Set(visible.map(b => b.id));
  const shownFeatured = featured.filter(f => visibleIds.has(f.book));
  if (shownFeatured.length) {
    html += `<div class="pinned-row">`;
    for (const f of shownFeatured) {
      const label = lang === "en" ? f.label_en : f.label_gu;
      html += `<a class="pinned-chip" href="#/book/${f.book}/${f.section}">
        <span class="pin-glyph">${lang === "en" ? "||" : "॥"}</span>
        <span><strong>${escapeHtml(label)}</strong></span>
      </a>`;
    }
    html += `</div>`;
  }
  // resume card: only for a book readable in the CURRENT language, and its
  // section title is derived live (never replayed from whatever language it
  // was stored in)
  const lastBook = last && visible.find(b => b.id === last.book);
  if (lastBook) {
    const lastEn = lang === "en" ? await loadEn(last.book) : null;
    const lastFull = await loadBook(last.book);
    const secLabel = lastFull.sections[last.section]
      ? secTitle(lastFull, lastEn, last.section) : "";
    html += `<a class="continue-card" href="#/book/${last.book}/${last.section}">
      <div class="label">${escapeHtml(t("continueL"))}</div>
      <h3>${escapeHtml(bt(lastBook))}</h3>
      ${secLabel ? `<div class="sub">${escapeHtml(secLabel)}</div>` : ""}</a>`;
  }
  for (const b of visible) {
    html += `<a class="book-card" href="#/book/${b.id}">
      <h3>${escapeHtml(bt(b))}</h3>
      <div class="meta">${b.sections_count} ${b.language === "translit" ? t("compositions") : t("sections")} · ${b.pages} ${t("pagesW")}</div>
    </a>`;
  }
  html += `</div>`;
  if (stale(tok)) return;
  view.innerHTML = html;
  restoreScroll();
}

/* ---------------- table of contents ---------------- */
async function renderToc(bookId, tok) {
  const book = await loadBook(bookId);
  const en = lang === "en" ? await loadEn(bookId) : null;
  if (stale(tok)) return;
  setTitle(bt(book));
  let html = `<div class="reveal">`;
  book.sections.forEach((s, i) => {
    const e = enSec(en, i);
    const sub = lang === "en" && e && e.title_en
      ? `<br><small style="color:var(--ink-soft)">${escapeHtml(e.title_en)}</small>` : "";
    html += `<a class="toc-item" href="#/book/${bookId}/${i}">
      <span class="n">${i + 1}</span>
      <span class="t">${escapeHtml(secTitle(book, en, i))}${sub}</span>
      <span class="pg">${s.page_start ? t("pageAbbr") + " " + s.page_start : ""}</span>
    </a>`;
  });
  html += `</div>`;
  if (stale(tok)) return;
  view.innerHTML = html;
  restoreScroll();
}

/* ---------------- reader ---------------- */
async function renderReader(bookId, idx, tok) {
  const book = await loadBook(bookId);
  if (stale(tok)) return;
  const s = book.sections[idx];
  if (!s) return renderToc(bookId, tok);
  // a Latin-content volume must never render in Gujarati mode: send the
  // reader to its Gujarati counterpart instead of showing the wrong script
  if (book.language === "translit" && lang !== "en") {
    const back = crossLink(bookId, idx);
    // replaceState, not a hash assignment: pushing a new entry would let Back
    // return to the hidden volume and bounce forward again forever
    const target = back ? `#/book/${back.book}/${back.section}` : "#/";
    history.replaceState({ lang }, "", location.pathname + location.search + target);
    prevHash = target;
    return route();
  }
  const en = lang === "en" ? await loadEn(bookId) : null;
  if (stale(tok)) return;          // abandoned route must not retitle or
  const e = enSec(en, idx);        // overwrite the resume position
  setTitle(bt(book));
  store.set("lastRead", { book: bookId, section: idx });

  let body = "";
  if (lang === "en" && e && (e.translit || e.translation)) {
    // full English edition: pronunciation + meaning, no Gujarati on screen.
    // Kirtans 1-31 carry no generated translit (the printed English edition
    // IS the pronunciation) — pull it inline from the English volume.
    let translit = e.translit;
    if (!translit) {
      const xl0 = crossLink(bookId, idx);
      if (xl0) {
        const enBook = await loadBook(xl0.book);
        const xs = enBook.sections[xl0.section];
        if (xs) {
          translit = xs.blocks.map(b => b.text).join("\n\n");
          // the printed edition's page flow can carry the previous
          // composition's tail — start at this composition's ATH opening
          const at = translit.search(/ATH\s+SH?REE?\s|ATH\s+SHRI\s/i);
          if (at > 0) translit = translit.slice(at);
        }
      }
    }
    if (translit) body += `<div class="block en-translit">${escapeHtml(translit)}</div>`;
    if (e.translation) {
      if (translit) body += `<h4 class="saar-h">MEANING</h4>`;
      body += `<div class="block en-translation">${escapeHtml(e.translation)}</div>`;
    }
  } else {
    let lastPage = null;
    for (const blk of s.blocks) {
      if (blk.page && blk.page !== lastPage) { body += `<div class="pageref">${blk.page}</div>`; lastPage = blk.page; }
      // a predominantly Devanagari block gets the Devanagari face first, so
      // its dandas (। ॥) match the verse rather than borrowing the Gujarati cut
      const cls = (blk.sub ? "subhead" : "block") + devClass(blk.text);
      body += `<div class="${cls}">${escapeHtml(blk.text)}</div>`;
    }
  }
  const bmKey = `${bookId}/${idx}`;
  const marked = store.get("bookmarks", []).some(b => b.key === bmKey);
  const xl = crossLink(bookId, idx);
  // switching volumes must switch LANGUAGE too: the English volume is hidden in
  // Gujarati mode and would immediately redirect back, making the link a no-op
  const xlHtml = xl ? `<div class="src-link"><a href="${bookHref(xl.book, xl.section, xl.lang)}">${escapeHtml(xl.label)}</a></div>` : "";
  const prev = idx > 0 ? `<a href="#/book/${bookId}/${idx - 1}">‹ ${escapeHtml(secTitle(book, en, idx - 1))}</a>` : "<span></span>";
  const next = idx < book.sections.length - 1 ? `<a href="#/book/${bookId}/${idx + 1}">${escapeHtml(secTitle(book, en, idx + 1))} ›</a>` : "<span></span>";
  const headSub = lang === "en" && e && e.title_en
    ? `<div class="sub-en">${escapeHtml(e.title_en)}</div>` : "";

  if (stale(tok)) return;

  // Paginated (book-like) reading: the content is laid out in CSS columns the
  // width of the viewport and moved sideways one page at a time.
  view.innerHTML = `<div id="pager" class="pager">
    <div id="pages" class="pages"><article class="reader">
      <div class="section-head">
        <div class="deco">${lang === "en" ? "|| ✻ ||" : "॥ ✻ ॥"}</div>
        <h2>${escapeHtml(secTitle(book, en, idx))}</h2>${headSub}
      </div>
      ${xlHtml}
      ${body}
      <div class="bookmark-row">
        <button id="bm-toggle" class="${marked ? "on" : ""}">${marked ? t("bmOn") : t("bmOff")}</button>
      </div>
      <div class="reader-nav">${prev}${next}</div>
    </article></div>
    <div class="page-edge left" aria-hidden="true"></div>
    <div class="page-edge right" aria-hidden="true"></div>
    <div id="page-count" class="page-count" role="status" aria-live="polite"></div>
  </div>`;
  setupPager(bookId, idx, book, tok);

  $("#bm-toggle").addEventListener("click", () => {
    let bms = store.get("bookmarks", []);
    if (bms.some(b => b.key === bmKey)) bms = bms.filter(b => b.key !== bmKey);
    else bms.push({ key: bmKey, book: bookId, section: idx });
    store.set("bookmarks", bms);
    const on = bms.some(b => b.key === bmKey);
    $("#bm-toggle").classList.toggle("on", on);
    $("#bm-toggle").textContent = on ? t("bmOn") : t("bmOff");
  });
}

/* ---------------- saar (essence / teachings) ---------------- */
function pearlCard(tj) {
  const p = todaysPearl(tj);
  const firstLine = (lang === "en" ? p.u.verse_translit : p.u.verse_gu).split(/[;\n]/)[0];
  const sub = lang === "en" ? `${p.u.title_translit} · ${p.u.title_en}` : p.u.title_gu;
  return `<a class="pearl-card" href="#/saar/${p.ti}/${p.ui}">
    <div class="label">✦ ${escapeHtml(t("pearlLabel"))}</div>
    <div class="pearl-verse">${escapeHtml(firstLine)}</div>
    <div class="pearl-title">${escapeHtml(sub)}</div>
  </a>`;
}

async function renderSaar(tok) {
  const tj = await loadTeachings();
  if (stale(tok)) return;
  setTitle(t("saarTitle"));
  let html = `<div class="reveal">`;
  html += pearlCard(tj);
  html += `<a class="book-card" href="#/saar/story">
    <h3>${escapeHtml(lang === "en" ? tj.story.title_en : tj.story.title_gu)}</h3></a>`;
  tj.themes.forEach((th, ti) => {
    html += `<a class="book-card" href="#/saar/${ti}">
      <h3>${escapeHtml(lang === "en" ? th.title_en : th.title_gu)}</h3>
      <div class="meta">${th.units.length} ${escapeHtml(t("pearls"))}</div></a>`;
  });
  if (stale(tok)) return;
  view.innerHTML = html + `</div>`;
  restoreScroll();
}

async function renderStory(tok) {
  const tj = await loadTeachings();
  if (stale(tok)) return;
  setTitle(lang === "en" ? tj.story.title_en : tj.story.title_gu);
  const s = tj.story;
  const body = lang === "en" ? s.body_en : (s.body_gu || s.body_en);
  const verse = lang === "en" ? (s.anchor_verse_translit || "") : s.anchor_verse;
  let html = `<article class="reader saar-story">
    <div class="section-head"><div class="deco">${lang === "en" ? "|| ✦ ||" : "॥ ✦ ॥"}</div>
    <h2>${escapeHtml(lang === "en" ? s.title_en : s.title_gu)}</h2></div>`;
  for (const p of body) html += `<p class="story-p">${escapeHtml(p)}</p>`;
  html += `<div class="unit-verse${devClass(verse)}">${escapeHtml(verse)}</div>
    <p class="story-p muted">${escapeHtml(lang === "en" ? s.anchor_meaning_en : (s.anchor_meaning_gu || s.anchor_meaning_en))}</p>
    <div class="src-link"><a href="#/book/${s.anchor_source.book}/${s.anchor_source.section}">${escapeHtml(t("readInBook"))} ${escapeHtml(pageLabel(s.anchor_source))}</a></div>
    <p class="caveat">${escapeHtml(lang === "en" ? s.caveat_en : (s.caveat_gu || s.caveat_en))}</p></article>`;
  if (stale(tok)) return;
  view.innerHTML = html;
  restoreScroll();
}

async function renderTheme(ti, tok) {
  const tj = await loadTeachings();
  const th = tj.themes[ti];
  if (!th) return renderSaar(tok);
  if (stale(tok)) return;
  setTitle(lang === "en" ? th.title_en : th.title_gu);
  const intro = lang === "en" ? th.intro_en : (th.intro_gu || th.intro_en);
  let html = `<div class="reveal"><p class="theme-intro">${escapeHtml(intro)}</p>`;
  th.units.forEach((u, ui) => {
    const main = lang === "en" ? u.title_en : u.title_gu;
    const small = lang === "en" ? u.title_translit : "";
    html += `<a class="toc-item" href="#/saar/${ti}/${ui}">
      <span class="n">✦</span>
      <span class="t">${escapeHtml(main)}${small ? `<br><small style="color:var(--ink-soft)">${escapeHtml(small)}</small>` : ""}</span></a>`;
  });
  if (stale(tok)) return;
  view.innerHTML = html + `</div>`;
  restoreScroll();
}

async function renderUnit(ti, ui, tok) {
  const tj = await loadTeachings();
  const th = tj.themes[ti], u = th && th.units[ui];
  if (!u) return renderSaar(tok);
  if (stale(tok)) return;
  setTitle(lang === "en" ? th.title_en : th.title_gu);
  const src = u.source;
  const gloss = u.gloss.map((g, gi) => {
    const word = lang === "en" ? (g.word_translit || g.word) : g.word;
    const mean = lang === "en" ? g.meaning : ((u.gloss_gu || [])[gi] || g.meaning);
    return `<div class="gloss-item"><span class="g-word">${escapeHtml(word)}</span><span class="g-mean">${escapeHtml(mean)}</span></div>`;
  }).join("");
  const alt = src.alt_book ? ` · <a href="${bookHref(src.alt_book, src.alt_section, "en")}">${lang === "en" ? "English" : "અંગ્રેજી"}</a>` : "";
  const uTitle = x => lang === "en" ? x.title_en : x.title_gu;
  const prev = ui > 0 ? `<a href="#/saar/${ti}/${ui - 1}">‹ ${escapeHtml(uTitle(th.units[ui - 1]))}</a>` : "<span></span>";
  const next = ui < th.units.length - 1 ? `<a href="#/saar/${ti}/${ui + 1}">${escapeHtml(uTitle(th.units[ui + 1]))} ›</a>` : "<span></span>";
  const verse = lang === "en" ? u.verse_translit : u.verse_gu;
  const translitLine = lang === "en" ? "" : "";
  if (stale(tok)) return;
  view.innerHTML = `<article class="reader saar-unit reveal">
    <div class="section-head"><div class="deco">${lang === "en" ? "|| ✦ ||" : "॥ ✦ ॥"}</div>
      <h2>${escapeHtml(uTitle(u))}</h2>
      ${lang === "en" ? `<div class="sub-en">${escapeHtml(u.title_translit || "")}</div>` : ""}</div>
    <div class="unit-verse${devClass(verse)}">${escapeHtml(verse)}</div>
    ${translitLine}
    <div class="src-link"><a href="#/book/${src.book}/${src.section}">${escapeHtml(t("readInBook"))} ${escapeHtml(pageLabel(src))}</a>${alt}</div>
    <h4 class="saar-h">${escapeHtml(t("gloss"))}</h4><div class="gloss">${gloss}</div>
    <h4 class="saar-h">${escapeHtml(t("meaning"))}</h4><p class="story-p">${escapeHtml(uf(u, "meaning"))}</p>
    <h4 class="saar-h">${escapeHtml(t("why"))}</h4><p class="story-p">${escapeHtml(uf(u, "why"))}</p>
    <div class="reflect">✦ ${escapeHtml(uf(u, "reflect"))}</div>
    <div class="reader-nav">${prev}${next}</div>
  </article>`;
  restoreScroll();
}


/* ---------------- paginated reader (book-style pages) ----------------
   Content flows into CSS columns exactly one viewport wide, and turning a page
   translates the column track. Works for any script, respects the font-size
   control, and re-lays out on resize / rotation / device fold. */
let pagerState = null;

function pagerKey() { return "pg:" + scrollKey(); }

function setupPager(bookId, idx, book, tok) {
  const pager = $("#pager"), track = $("#pages");
  if (!pager || !track) return;

  const FOOT = 26, GAP = 32;
  let lastW = 0;
  const measure = () => {
    // one column per ~29rem: phone = 1, iPad/unfolded = 2. The page itself is
    // capped so a single column never becomes an uncomfortably long line.
    const avail = (pager.parentElement || pager).clientWidth;
    const cols = Math.max(1, Math.min(2, Math.floor(avail / 460)));
    pager.style.maxWidth = (cols === 1 ? 680 : 1180) + "px";
    const w = track.clientWidth;
    track.style.columnWidth = ((w - GAP * (cols - 1)) / cols) + "px";
    track.style.columnGap = GAP + "px";
    // leave room for the page counter so the last line never sits under it
    track.style.height = Math.max(120, pager.clientHeight - FOOT) + "px";
    lastW = w;
    const step = w + GAP;
    const total = Math.max(1, Math.ceil((track.scrollWidth + GAP) / step));
    return { step, total, cols };
  };

  let { step, total } = measure();
  let page = Math.min(scrollPositions[pagerKey()] || 0, total - 1);

  const paint = () => {
    track.style.transform = `translateX(${-page * step}px)`;
    $("#page-count").textContent = total > 1 ? `${page + 1} / ${total}` : "";
    pager.classList.toggle("at-start", page === 0);
    pager.classList.toggle("at-end", page >= total - 1);
    scrollPositions[pagerKey()] = page;
    persistScroll();
  };

  const go = (delta) => {
    // a resize delivered while the tab was hidden never reached the observer,
    // so the first interaction after it re-measures rather than jumping wrong
    if (track.clientWidth !== lastW) relayout();
    const next = page + delta;
    if (next < 0 || next >= total) {
      // past either end, continue into the neighbouring section — like a book
      const target = delta > 0 ? idx + 1 : idx - 1;
      if (target >= 0 && target < book.sections.length) {
        if (delta < 0) pendingLastPage = true;
        location.hash = `#/book/${bookId}/${target}`;
      }
      return;
    }
    page = next;
    paint();
  };

  const relayout = () => {
    const before = total > 1 ? page / (total - 1) : 0;
    ({ step, total } = measure());
    page = Math.min(Math.round(before * (total - 1)) || 0, total - 1);
    paint();
  };

  if (pendingLastPage) { page = total - 1; pendingLastPage = false; }
  paint();

  // swipe
  let x0 = null, y0 = null;
  pager.addEventListener("pointerdown", (e) => { x0 = e.clientX; y0 = e.clientY; });
  pager.addEventListener("pointerup", (e) => {
    if (x0 === null) return;
    const dx = e.clientX - x0, dy = e.clientY - y0;
    x0 = null;
    if (Math.abs(dx) > 45 && Math.abs(dx) > Math.abs(dy) * 1.5) { go(dx < 0 ? 1 : -1); return; }
    // a tap near either edge turns the page, like a reader app
    if (Math.abs(dx) < 12 && Math.abs(dy) < 12 && !e.target.closest("a,button")) {
      const rel = (e.clientX - pager.getBoundingClientRect().left) / pager.clientWidth;
      if (rel > 0.75) go(1); else if (rel < 0.25) go(-1);
    }
  });
  pager.addEventListener("keydown", (e) => {
    if (e.key === "ArrowRight" || e.key === "PageDown") { go(1); e.preventDefault(); }
    if (e.key === "ArrowLeft" || e.key === "PageUp") { go(-1); e.preventDefault(); }
  });
  pager.tabIndex = 0;

  // a rotate/fold reports its new size before the layout around it has settled,
  // so every resize is followed by one deferred re-measure
  let settle = 0;
  const onResize = () => {
    if (stale(tok)) return;
    relayout();
    clearTimeout(settle);
    settle = setTimeout(() => { if (!stale(tok)) relayout(); }, 90);
  };
  addEventListener("resize", onResize);
  document.addEventListener("visibilitychange", onResize);
  const ro = new ResizeObserver(onResize);
  ro.observe(pager);
  // fonts finish loading after first paint and change the column count
  if (document.fonts && document.fonts.ready) document.fonts.ready.then(() => { if (!stale(tok)) relayout(); });
  pagerState = { dispose() {
    removeEventListener("resize", onResize);
    document.removeEventListener("visibilitychange", onResize);
    ro.disconnect(); clearTimeout(settle);
  }, relayout };
}
let pendingLastPage = false;

/* ---------------- bookmarks ---------------- */
async function renderBookmarks(tok) {
  setTitle(t("marksTitle"));
  const bms = store.get("bookmarks", []);
  const books = await loadManifest();
  // titles derived live in the current language; a bookmark in a volume that
  // does not exist in this language is hidden rather than shown in the wrong script
  const rows = [];
  for (const b of bms) {
    const meta = books.find(x => x.id === b.book);
    if (!meta || (meta.language === "translit" && lang !== "en")) continue;
    const full = await loadBook(b.book);
    if (!full.sections[b.section]) continue;
    const en = lang === "en" ? await loadEn(b.book) : null;
    rows.push({ ...b, secLabel: secTitle(full, en, b.section), bookLabel: bt(meta) });
  }
  if (!rows.length) {
    if (stale(tok)) return;
    view.innerHTML = `<div class="empty"><span class="glyph">✻</span>${t("bmEmpty")}</div>`;
    return;
  }
  let html = `<div class="reveal">`;
  for (const b of rows) {
    html += `<a class="toc-item" href="#/book/${b.book}/${b.section}">
      <span class="n">✻</span>
      <span class="t">${escapeHtml(b.secLabel)}<br><small style="color:var(--ink-soft)">${escapeHtml(b.bookLabel)}</small></span>
    </a>`;
  }
  if (stale(tok)) return;
  view.innerHTML = html + `</div>`;
  restoreScroll();
}

/* ---------------- search ---------------- */
/* One index per language: Gujarati mode searches the scripture text;
   English mode searches the English edition. Labels are NOT baked in —
   only ids, so results render in whatever language is active. */
const indexes = {};
async function buildIndex() {
  // pin the language for the whole (async) build — reading the global mid-build
  // would splice two languages into one index if the user toggles while it runs
  const L = lang;
  if (indexes[L]) return indexes[L];
  const books = await loadManifest();
  const idx = [];
  for (const b of books) {
    if (b.language === "translit" && L !== "en") continue;
    const book = await loadBook(b.id);
    const en = L === "en" ? await loadEn(b.id) : null;
    book.sections.forEach((s, si) => {
      if (L === "en") {
        const e = enSec(en, si);
        const text = e ? [e.translit, e.translation].filter(Boolean).join("\n")
                       : (b.language === "translit" ? s.blocks.map(x => x.text).join("\n") : "");
        if (text.trim()) idx.push({ book: b.id, section: si, page: null, raw: text, norm: normalize(text) });
      } else {
        s.blocks.forEach(blk => idx.push({
          book: b.id, section: si, page: blk.page || null,
          raw: blk.text, norm: normalize(blk.text),
        }));
      }
    });
  }
  indexes[L] = idx;
  return idx;
}

let searchTimer = null;
let searchGen = 0;      // a newer query (or a cleared field) invalidates older ones
async function renderSearch(initial, tok) {
  setTitle(t("searchTitle"), { keepFocus: true });
  if (stale(tok)) return;
  view.innerHTML = `
    <div class="search-wrap">
      <input id="search-input" type="search" autocomplete="off"
        placeholder="${escapeHtml(t("searchPh"))}" value="${escapeHtml(initial)}">
    </div>
    <div class="search-hint">${escapeHtml(t("searchHint"))}</div>
    <p id="search-status" role="status" aria-live="polite" class="search-hint"></p>\n    <div id="results"></div>`;
  const input = $("#search-input");
  input.addEventListener("input", () => {
    searchGen++;            // any in-flight search is stale from this instant
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => {
      // mirror the query into the hash so a language switch or reload keeps it
      const q = input.value.trim();
      const want = q ? `#/search/${encodeURIComponent(q)}` : "#/search";
      if (location.hash !== want) {
        history.replaceState({ lang, eid: entryId }, "", want);
        prevHash = want; prevKey = scrollKey();
      }
      runSearch(input.value);
    }, 250);
  });
  input.focus();
  input.setSelectionRange(input.value.length, input.value.length);
  if (initial) runSearch(initial);
}

async function runSearch(q) {
  const gen = ++searchGen;               // clearing the field bumps this too,
  const resEl = $("#results");           // so an in-flight search cannot paint
  const nq = normalize(q);
  if (nq.length < 2) {
    resEl.innerHTML = "";
    const st = $("#search-status");
    if (st) st.textContent = q ? "" : t("searchCleared");
    return;
  }
  const statusEl = $("#search-status");
  if (statusEl) statusEl.textContent = t("searching");
  const idx = await buildIndex();
  if (gen !== searchGen) return;
  const out = [];
  for (const e of idx) {
    if (e.norm.includes(nq)) {
      out.push(e);
      if (out.length >= 80) break;
    }
  }
  if (!out.length) {
    if (statusEl) statusEl.textContent = t("noResults");
    resEl.innerHTML = `<div class="empty"><span class="glyph">॥</span>${escapeHtml(t("noResults"))}</div>`;
    return;
  }
  if (statusEl) statusEl.textContent = `${out.length}${out.length > 50 ? "+" : ""} ${t("results")}`;
  const books = await loadManifest();
  if (gen !== searchGen) return;
  let html = "";
  for (const e of out.slice(0, 50)) {
    const meta = books.find(b => b.id === e.book);
    const full = await loadBook(e.book);
    const enB = lang === "en" ? await loadEn(e.book) : null;
    const where = `${escapeHtml(bt(meta))} · ${escapeHtml(secTitle(full, enB, e.section))}` +
      (e.page ? " · " + t("pageAbbr") + " " + e.page : "");
    html += `<a class="result" href="#/book/${e.book}/${e.section}">
      <div class="where">${where}</div>
      <div class="snip">${snippet(e.raw, q)}</div>
    </a>`;
  }
  if (out.length > 50) html += `<div class="search-hint">${out.length}+ ${escapeHtml(t("moreResults"))}</div>`;
  if (gen !== searchGen) return;
  resEl.innerHTML = html;
}

function snippet(raw, q) {
  /* try exact raw highlight; else show block start */
  const flat = raw.replace(/\s+/g, " ");
  const pos = flat.toLowerCase().indexOf(q.toLowerCase());
  if (pos >= 0) {
    const a = Math.max(0, pos - 45), b = Math.min(flat.length, pos + q.length + 60);
    return (a > 0 ? "…" : "") + escapeHtml(flat.slice(a, pos)) +
      "<mark>" + escapeHtml(flat.slice(pos, pos + q.length)) + "</mark>" +
      escapeHtml(flat.slice(pos + q.length, b)) + (b < flat.length ? "…" : "");
  }
  return escapeHtml(flat.slice(0, 110)) + (flat.length > 110 ? "…" : "");
}

/* ---------------- service worker ---------------- */
if ("serviceWorker" in navigator && location.protocol !== "file:") {
  addEventListener("load", () => navigator.serviceWorker.register("sw.js"));
}
