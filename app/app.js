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
};
let lang = store.get("lang", "gu");
function t(key) { return (STR[key] || {})[lang] || (STR[key] || {}).gu || key; }
function applyLang() {
  document.documentElement.lang = lang;
  const btn = $("#lang-btn");
  if (btn) btn.textContent = lang === "gu" ? "EN" : "ગુ";
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
    return { book: "kirtan-english", section: idx - 1, label: t("toEnglish") };
  if (bookId === "kirtan-english" && idx <= 30)
    return { book: "kirtan-gujarati", section: idx + 1, label: t("toGujarati") };
  return null;
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
  lang = lang === "gu" ? "en" : "gu";
  store.set("lang", lang);
  applyLang();
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
async function loadBook(id) {
  if (!bookCache[id]) bookCache[id] = await (await fetch(`content/${id}.json`)).json();
  return bookCache[id];
}
const enCache = {};
async function loadEn(id) {
  if (!(id in enCache)) {
    try { enCache[id] = await (await fetch(`content/en/${id}.json`)).json(); }
    catch { enCache[id] = null; }
  }
  return enCache[id];
}
function enSec(en, idx) { return (en && en.sections && en.sections[idx]) || null; }
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
window.addEventListener("hashchange", route);
window.addEventListener("DOMContentLoaded", route);

function parseHash() {
  const h = location.hash.replace(/^#\/?/, "");
  return h.split("/").filter(Boolean);
}

async function route() {
  const parts = parseHash();
  const navKey = parts[0] === "search" ? "search" : parts[0] === "bookmarks" ? "bookmarks"
    : parts[0] === "saar" ? "saar" : "library";
  document.querySelectorAll("#bottomnav a").forEach(a =>
    a.classList.toggle("active", a.dataset.nav === navKey));

  const readerMode = parts[0] === "book" && parts.length >= 3;
  $("#font-plus").hidden = $("#font-minus").hidden = !readerMode;
  $("#back-btn").hidden = parts.length === 0;

  try {
    if (parts.length === 0) return renderLibrary();
    if (parts[0] === "search") return renderSearch(decodeURIComponent(parts[1] || ""));
    if (parts[0] === "bookmarks") return renderBookmarks();
    if (parts[0] === "saar" && parts[1] === "story") return renderStory();
    if (parts[0] === "saar" && parts.length === 3) return renderUnit(+parts[1], +parts[2]);
    if (parts[0] === "saar" && parts.length === 2) return renderTheme(+parts[1]);
    if (parts[0] === "saar") return renderSaar();
    if (parts[0] === "book" && parts.length === 2) return renderToc(parts[1]);
    if (parts[0] === "book" && parts.length >= 3) return renderReader(parts[1], parseInt(parts[2], 10));
    renderLibrary();
  } catch (err) {
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

function setTitle(t) { $("#topbar-text").textContent = t; }
function escapeHtml(s) {
  return s.replace(/[&<>"']/g, c => ({ "&":"&amp;", "<":"&lt;", ">":"&gt;", '"':"&quot;", "'":"&#39;" }[c]));
}

/* ---------------- library ---------------- */
async function renderLibrary() {
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
  if (featured.length) {
    html += `<div class="pinned-row">`;
    for (const f of featured) {
      const label = lang === "en" ? f.label_en : f.label_gu;
      html += `<a class="pinned-chip" href="#/book/${f.book}/${f.section}">
        <span class="pin-glyph">${lang === "en" ? "||" : "॥"}</span>
        <span><strong>${escapeHtml(label)}</strong></span>
      </a>`;
    }
    html += `</div>`;
  }
  if (last && books.find(b => b.id === last.book)) {
    const b = books.find(bb => bb.id === last.book);
    html += `<a class="continue-card" href="#/book/${last.book}/${last.section}">
      <div class="label">${escapeHtml(t("continueL"))}</div>
      <h3>${escapeHtml(bt(b))}</h3>
      ${lang === "en" ? "" : `<div class="sub">${escapeHtml(last.sectionTitle || "")}</div>`}</a>`;
  }
  for (const b of books) {
    html += `<a class="book-card" href="#/book/${b.id}">
      <h3>${escapeHtml(bt(b))}</h3>
      <div class="meta">${b.sections_count} ${b.language === "translit" ? t("compositions") : t("sections")} · ${b.pages} ${t("pagesW")}</div>
    </a>`;
  }
  html += `</div>`;
  view.innerHTML = html;
  window.scrollTo(0, 0);
}

/* ---------------- table of contents ---------------- */
async function renderToc(bookId) {
  const book = await loadBook(bookId);
  const en = lang === "en" ? await loadEn(bookId) : null;
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
  view.innerHTML = html;
  window.scrollTo(0, 0);
}

/* ---------------- reader ---------------- */
async function renderReader(bookId, idx) {
  const book = await loadBook(bookId);
  const s = book.sections[idx];
  if (!s) return renderToc(bookId);
  const en = lang === "en" ? await loadEn(bookId) : null;
  const e = enSec(en, idx);
  setTitle(bt(book));
  store.set("lastRead", { book: bookId, section: idx, sectionTitle: s.title });

  let body = "";
  if (lang === "en" && e && (e.translit || e.translation)) {
    // full English edition: pronunciation + meaning, no Gujarati on screen
    if (e.translit) body += `<div class="block en-translit">${escapeHtml(e.translit)}</div>`;
    if (e.translation) {
      if (e.translit) body += `<h4 class="saar-h">MEANING</h4>`;
      body += `<div class="block en-translation">${escapeHtml(e.translation)}</div>`;
    }
  } else {
    let lastPage = null;
    for (const blk of s.blocks) {
      if (blk.page && blk.page !== lastPage) { body += `<div class="pageref">${blk.page}</div>`; lastPage = blk.page; }
      body += blk.sub
        ? `<div class="subhead">${escapeHtml(blk.text)}</div>`
        : `<div class="block">${escapeHtml(blk.text)}</div>`;
    }
  }
  const bmKey = `${bookId}/${idx}`;
  const marked = store.get("bookmarks", []).some(b => b.key === bmKey);
  const xl = crossLink(bookId, idx);
  const xlHtml = xl ? `<div class="src-link"><a href="#/book/${xl.book}/${xl.section}">${escapeHtml(xl.label)}</a></div>` : "";
  const prev = idx > 0 ? `<a href="#/book/${bookId}/${idx - 1}">‹ ${escapeHtml(secTitle(book, en, idx - 1))}</a>` : "<span></span>";
  const next = idx < book.sections.length - 1 ? `<a href="#/book/${bookId}/${idx + 1}">${escapeHtml(secTitle(book, en, idx + 1))} ›</a>` : "<span></span>";
  const headSub = lang === "en" && e && e.title_en
    ? `<div class="sub-en">${escapeHtml(e.title_en)}</div>` : "";

  view.innerHTML = `<article class="reader">
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
  </article>`;
  window.scrollTo(0, 0);

  $("#bm-toggle").addEventListener("click", () => {
    let bms = store.get("bookmarks", []);
    if (bms.some(b => b.key === bmKey)) bms = bms.filter(b => b.key !== bmKey);
    else bms.push({ key: bmKey, book: bookId, section: idx, title: s.title, bookTitle: book.title_gu });
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

async function renderSaar() {
  setTitle(t("saarTitle"));
  const tj = await loadTeachings();
  let html = `<div class="reveal">`;
  html += pearlCard(tj);
  html += `<a class="book-card" href="#/saar/story">
    <h3>${escapeHtml(lang === "en" ? tj.story.title_en : tj.story.title_gu)}</h3></a>`;
  tj.themes.forEach((th, ti) => {
    html += `<a class="book-card" href="#/saar/${ti}">
      <h3>${escapeHtml(lang === "en" ? th.title_en : th.title_gu)}</h3>
      <div class="meta">${th.units.length} ${escapeHtml(t("pearls"))}</div></a>`;
  });
  view.innerHTML = html + `</div>`;
  window.scrollTo(0, 0);
}

async function renderStory() {
  const tj = await loadTeachings();
  setTitle(lang === "en" ? tj.story.title_en : tj.story.title_gu);
  const s = tj.story;
  const body = lang === "en" ? s.body_en : (s.body_gu || s.body_en);
  const verse = lang === "en" ? (s.anchor_verse_translit || "") : s.anchor_verse;
  let html = `<article class="reader saar-story">
    <div class="section-head"><div class="deco">${lang === "en" ? "|| ✦ ||" : "॥ ✦ ॥"}</div>
    <h2>${escapeHtml(lang === "en" ? s.title_en : s.title_gu)}</h2></div>`;
  for (const p of body) html += `<p class="story-p">${escapeHtml(p)}</p>`;
  html += `<div class="unit-verse">${escapeHtml(verse)}</div>
    <p class="story-p muted">${escapeHtml(lang === "en" ? s.anchor_meaning_en : (s.anchor_meaning_gu || s.anchor_meaning_en))}</p>
    <div class="src-link"><a href="#/book/${s.anchor_source.book}/${s.anchor_source.section}">${escapeHtml(t("readInBook"))} ${escapeHtml(pageLabel(s.anchor_source))}</a></div>
    <p class="caveat">${escapeHtml(lang === "en" ? s.caveat_en : (s.caveat_gu || s.caveat_en))}</p></article>`;
  view.innerHTML = html;
  window.scrollTo(0, 0);
}

async function renderTheme(ti) {
  const tj = await loadTeachings();
  const th = tj.themes[ti];
  if (!th) return renderSaar();
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
  view.innerHTML = html + `</div>`;
  window.scrollTo(0, 0);
}

async function renderUnit(ti, ui) {
  const tj = await loadTeachings();
  const th = tj.themes[ti], u = th && th.units[ui];
  if (!u) return renderSaar();
  setTitle(lang === "en" ? th.title_en : th.title_gu);
  const src = u.source;
  const gloss = u.gloss.map((g, gi) => {
    const word = lang === "en" ? (g.word_translit || g.word) : g.word;
    const mean = lang === "en" ? g.meaning : ((u.gloss_gu || [])[gi] || g.meaning);
    return `<div class="gloss-item"><span class="g-word">${escapeHtml(word)}</span><span class="g-mean">${escapeHtml(mean)}</span></div>`;
  }).join("");
  const alt = src.alt_book ? ` · <a href="#/book/${src.alt_book}/${src.alt_section}">${lang === "en" ? "English" : "અંગ્રેજી"}</a>` : "";
  const uTitle = x => lang === "en" ? x.title_en : x.title_gu;
  const prev = ui > 0 ? `<a href="#/saar/${ti}/${ui - 1}">‹ ${escapeHtml(uTitle(th.units[ui - 1]))}</a>` : "<span></span>";
  const next = ui < th.units.length - 1 ? `<a href="#/saar/${ti}/${ui + 1}">${escapeHtml(uTitle(th.units[ui + 1]))} ›</a>` : "<span></span>";
  const verse = lang === "en" ? u.verse_translit : u.verse_gu;
  const translitLine = lang === "en" ? "" : "";
  view.innerHTML = `<article class="reader saar-unit reveal">
    <div class="section-head"><div class="deco">${lang === "en" ? "|| ✦ ||" : "॥ ✦ ॥"}</div>
      <h2>${escapeHtml(uTitle(u))}</h2>
      ${lang === "en" ? `<div class="sub-en">${escapeHtml(u.title_translit || "")}</div>` : ""}</div>
    <div class="unit-verse">${escapeHtml(verse)}</div>
    ${translitLine}
    <div class="src-link"><a href="#/book/${src.book}/${src.section}">${escapeHtml(t("readInBook"))} ${escapeHtml(pageLabel(src))}</a>${alt}</div>
    <h4 class="saar-h">${escapeHtml(t("gloss"))}</h4><div class="gloss">${gloss}</div>
    <h4 class="saar-h">${escapeHtml(t("meaning"))}</h4><p class="story-p">${escapeHtml(uf(u, "meaning"))}</p>
    <h4 class="saar-h">${escapeHtml(t("why"))}</h4><p class="story-p">${escapeHtml(uf(u, "why"))}</p>
    <div class="reflect">✦ ${escapeHtml(uf(u, "reflect"))}</div>
    <div class="reader-nav">${prev}${next}</div>
  </article>`;
  window.scrollTo(0, 0);
}

/* ---------------- bookmarks ---------------- */
function renderBookmarks() {
  setTitle(t("marksTitle"));
  const bms = store.get("bookmarks", []);
  if (!bms.length) {
    view.innerHTML = `<div class="empty"><span class="glyph">✻</span>${t("bmEmpty")}</div>`;
    return;
  }
  let html = `<div class="reveal">`;
  for (const b of bms) {
    html += `<a class="toc-item" href="#/book/${b.book}/${b.section}">
      <span class="n">✻</span>
      <span class="t">${escapeHtml(b.title)}<br><small style="color:var(--ink-soft)">${escapeHtml(b.bookTitle)}</small></span>
    </a>`;
  }
  view.innerHTML = html + `</div>`;
}

/* ---------------- search ---------------- */
async function buildIndex() {
  if (searchIndex) return searchIndex;
  const books = await loadManifest();
  searchIndex = [];
  for (const b of books) {
    const book = await loadBook(b.id);
    book.sections.forEach((s, si) => {
      s.blocks.forEach(blk => {
        searchIndex.push({
          book: b.id, bookTitle: b.title_gu, section: si, sectionTitle: s.title,
          page: blk.page || null, raw: blk.text, norm: normalize(blk.text),
        });
      });
    });
  }
  return searchIndex;
}

let searchTimer = null;
async function renderSearch(initial) {
  setTitle(t("searchTitle"));
  view.innerHTML = `
    <div class="search-wrap">
      <input id="search-input" type="search" autocomplete="off"
        placeholder="${escapeHtml(t("searchPh"))}" value="${escapeHtml(initial)}">
    </div>
    <div class="search-hint">${escapeHtml(t("searchHint"))}</div>
    <div id="results"></div>`;
  const input = $("#search-input");
  input.addEventListener("input", () => {
    clearTimeout(searchTimer);
    searchTimer = setTimeout(() => runSearch(input.value), 250);
  });
  if (initial) runSearch(initial);
  else input.focus();
}

async function runSearch(q) {
  const resEl = $("#results");
  const nq = normalize(q);
  if (nq.length < 2) { resEl.innerHTML = ""; return; }
  resEl.innerHTML = `<div class="search-hint">${escapeHtml(t("searching"))}</div>`;
  const idx = await buildIndex();
  const out = [];
  for (const e of idx) {
    if (e.norm.includes(nq)) {
      out.push(e);
      if (out.length >= 80) break;
    }
  }
  if (!out.length) {
    resEl.innerHTML = `<div class="empty"><span class="glyph">॥</span>${escapeHtml(t("noResults"))}</div>`;
    return;
  }
  let html = "";
  for (const e of out.slice(0, 50)) {
    html += `<a class="result" href="#/book/${e.book}/${e.section}">
      <div class="where">${escapeHtml(e.bookTitle)} · ${escapeHtml(e.sectionTitle)}${e.page ? " · " + t("pageAbbr") + " " + e.page : ""}</div>
      <div class="snip">${snippet(e.raw, q)}</div>
    </a>`;
  }
  if (out.length > 50) html += `<div class="search-hint">${out.length}+ ${escapeHtml(t("moreResults"))}</div>`;
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
