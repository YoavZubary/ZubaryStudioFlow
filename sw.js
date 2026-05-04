const CACHE = 'sf-v49';
const FILES = ['./', './index.html', './manifest.json', './icon.svg'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(FILES)));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys =>
    Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))
  ));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // Only intercept same-origin requests — let browser handle Drive, GAS, CDN, blob:, data: natively
  if (!e.request.url.startsWith(self.location.origin)) return;
  if (e.request.url.startsWith('blob:') || e.request.url.startsWith('data:')) return;
  e.respondWith(
    caches.match(e.request).then(cached => cached || fetch(e.request))
  );
});
