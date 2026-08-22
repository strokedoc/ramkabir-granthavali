/* Service worker: offline-first gutka.
   App shell precached; content JSON + fonts cached on first use. */
const VERSION = "v1";
const SHELL = ["./", "index.html", "styles.css", "app.js", "manifest.json", "icons/icon.svg"];

self.addEventListener("install", e => {
  e.waitUntil(caches.open("shell-" + VERSION).then(c => c.addAll(SHELL)).then(() => self.skipWaiting()));
});

self.addEventListener("activate", e => {
  e.waitUntil(
    caches.keys().then(keys => Promise.all(
      keys.filter(k => !k.endsWith(VERSION)).map(k => caches.delete(k))
    )).then(() => self.clients.claim())
  );
});

self.addEventListener("fetch", e => {
  const url = new URL(e.request.url);
  if (e.request.method !== "GET") return;

  /* content + fonts: cache-first, fill cache on first fetch */
  const runtime = url.pathname.includes("/content/") ||
    url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com";

  e.respondWith(
    caches.match(e.request).then(hit => {
      if (hit) return hit;
      return fetch(e.request).then(resp => {
        if (resp.ok || resp.type === "opaque") {
          const copy = resp.clone();
          caches.open((runtime ? "runtime-" : "shell-") + VERSION).then(c => c.put(e.request, copy));
        }
        return resp;
      }).catch(() => caches.match("index.html"));
    })
  );
});
