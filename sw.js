const CACHE_NAME = 'sales-assistant-v2.1';
const ASSETS = [
  './',
  './index.html',
  './sales-scripts.json',
  'https://cdn.tailwindcss.com',
  'https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js',
  'https://cdn.jsdelivr.net/npm/pinyin-pro@3.26.0/dist/index.js',
  'https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@400;500;700&display=swap',
];

self.addEventListener('install', e => {
  e.waitUntil(
    caches.open(CACHE_NAME).then(cache => cache.addAll(ASSETS))
  );
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(
    caches.keys().then(keys =>
      Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
    )
  );
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  // API 请求不缓存
  if (e.request.url.includes('/api/')) return;

  e.respondWith(
    caches.match(e.request).then(cached => {
      // 网络优先，失败时用缓存
      const fetched = fetch(e.request).then(res => {
        if (res.ok) {
          const clone = res.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(e.request, clone));
        }
        return res;
      }).catch(() => cached);
      return cached || fetched;
    })
  );
});
