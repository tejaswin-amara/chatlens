// KL Sync Service Worker — public app-shell cache only
const CACHE_NAME = 'kl-sync-cache-v2';
const STATIC_ASSETS = [
  '/',
  '/manifest.json',
  '/logo.webp',
  '/icon-192.png',
  '/icon-512.png',
];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => cache.addAll(STATIC_ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches
      .keys()
      .then((keys) =>
        Promise.all(
          keys
            .filter((key) => key !== CACHE_NAME)
            .map((key) => caches.delete(key))
        )
      )
  );
  self.clients.claim();
});

self.addEventListener('fetch', (event) => {
  const { request } = event;
  const url = new URL(request.url);

  // Never place API, authenticated, or user-specific responses in Cache Storage.
  if (url.origin !== self.location.origin || url.pathname.startsWith('/api/')) {
    return;
  }

  // Cache-first only for the explicitly public shell and immutable Next assets.
  if (
    request.method === 'GET' &&
    (url.pathname.startsWith('/_next/static/') ||
      STATIC_ASSETS.includes(url.pathname))
  ) {
    event.respondWith(
      caches.match(request).then(
        (cached) =>
          cached ||
          fetch(request).then((response) => {
            if (response.ok) {
              event.waitUntil(
                caches
                  .open(CACHE_NAME)
                  .then((cache) => cache.put(request, response.clone()))
              );
            }
            return response;
          })
      )
    );
  }
});
