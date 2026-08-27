/* Service worker: offline-first gutka.
   Whole library precached so every book reads offline from first install. */
const VERSION = "v40";
const PREFIX = "rkg-";
const SHELL = [
  "./", "index.html", "styles.css?v=40", "app.js?v=40", "manifest.json", "icons/icon.svg",
  "icons/icon-192.png", "icons/icon-512.png",
  "fonts/fonts.css?v=40",
  "fonts/dev0b591f69.woff2",
  "fonts/dev58a44ba7.woff2",
  "fonts/dev704492c5.woff2",
  "fonts/1fba8b406f.woff2",
  "fonts/62135b8fb7.woff2",
  "fonts/63f1654d1e.woff2",
  "fonts/64f2eab719.woff2",
  "fonts/abc66cb538.woff2",
  "fonts/b376e1cab3.woff2",
  "fonts/dedfa76904.woff2",
  "fonts/f2197f6858.woff2",
  "content/books.json", "content/teachings.json", "content/teachings-gu.json",
  "content/samagam-purvardh.json", "content/samagam-uttarardh.json",
  "content/sant-darshan.json", "content/kirtan-gujarati.json",
  "content/jivandas-sakhi.json", "content/kirtan-english.json",
  "content/en/samagam-purvardh.json", "content/en/samagam-uttarardh.json",
  "content/en/sant-darshan.json", "content/en/kirtan-gujarati.json",
  "content/en/jivandas-sakhi.json",
];

self.addEventListener("install", e => {
  // cache:"reload" bypasses the HTTP cache so a version bump always
  // precaches fresh files, never a stale heuristic-cached copy
  e.waitUntil(caches.open(PREFIX + "shell-" + VERSION)
    .then(c => c.addAll(SHELL.map(u => new Request(u, { cache: "reload" }))))
    .then(() => self.skipWaiting()));
});

const CURRENT = [PREFIX + "shell-" + VERSION, PREFIX + "runtime-" + VERSION];

// Cache storage is per-ORIGIN, and this origin also hosts other GitHub Pages
// projects, so a cache is ours to delete only if it holds requests inside our
// own scope. Matching on the PREFIX alone left the pre-prefix caches
// (shell-v2 / runtime-v2) alive forever, and a global caches.match() then
// answered every request from them — pinning existing readers to a build from
// before the prefix existed, with no way to ever receive an update.
async function isOurs(name) {
  const keys = await caches.open(name).then(c => c.keys());
  // judged on SAME-ORIGIN entries only: an old build also cached Google Fonts,
  // and requiring every entry to be in scope let that cache survive forever
  const own = keys.filter(r => new URL(r.url).origin === location.origin);
  return own.length > 0 && own.every(r => r.url.startsWith(self.registration.scope));
}

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) {
      if (!CURRENT.includes(k) && await isOurs(k)) await caches.delete(k);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  e.respondWith((async () => {
    // looked up ONLY in this version's caches: a global caches.match() also
    // searches caches this worker did not write, so a leftover one answers
    // first and the app can never move forward
    for (const name of CURRENT) {
      const hit = await caches.open(name).then(c => c.match(e.request));
      if (hit) return hit;
    }
    try {
      const resp = await fetch(e.request);
      // anything not precached is a genuine runtime miss: keep it in its own
      // bucket so it can never masquerade as a verified shell asset
      if (resp.ok && url.origin === location.origin) {
        const copy = resp.clone();
        caches.open(CURRENT[1]).then(c => c.put(e.request, copy));
      }
      return resp;
    } catch {
      return (await caches.open(CURRENT[0]).then(c => c.match("index.html")))
        || Response.error();
    }
  })());
});
