/* Service worker: offline-first gutka.
   Whole library precached so every book reads offline from first install. */
const VERSION = "v19";
const PREFIX = "rkg-";
const SHELL = [
  "./", "index.html", "styles.css?v=19", "app.js?v=19", "manifest.json", "icons/icon.svg",
  "icons/icon-192.png", "icons/icon-512.png",
  "fonts/fonts.css?v=19",
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

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      // delete only OUR old caches — never other apps' caches on this origin
      keys.filter(k => k.startsWith(PREFIX) && !k.endsWith(VERSION)).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;
  e.respondWith(
    caches.match(e.request).then(hit => {
      if (hit) return hit;
      return fetch(e.request).then(resp => {
        // anything not precached is a genuine runtime miss: keep it in its own
        // bucket so it can never masquerade as a verified shell asset
        if (resp.ok && url.origin === location.origin) {
          const copy = resp.clone();
          caches.open(PREFIX + "runtime-" + VERSION).then(c => c.put(e.request, copy));
        }
        return resp;
      }).catch(() => caches.match("index.html"));
    })
  );
});
