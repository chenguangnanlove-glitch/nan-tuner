/* 始信音乐 · 调音器 —— Service Worker
 *
 * 策略：
 *   - 页面导航  → 网络优先（保证永远拿到最新版），断网时用缓存兜底
 *   - 静态资源  → 缓存优先（图标等，秒开）
 *   - APK / 版本文件 → 完全不接管，永远走网络
 *
 * 改版后不需要手动改这个文件，CACHE 版本号变一次即可。
 */

const CACHE = 'shixin-tuner-v1';

const PRECACHE = [
  '/',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/favicon.png',
  '/manifest.webmanifest'
];

// 这些路径永远不缓存
const BYPASS = [/\.apk$/i, /app-version\.json$/i];

self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE)
      .then((c) => c.addAll(PRECACHE))
      .then(() => self.skipWaiting())
      .catch(() => self.skipWaiting())
  );
});

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(
        keys.filter((k) => k !== CACHE).map((k) => caches.delete(k))
      ))
      .then(() => self.clients.claim())
  );
});

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;              // 站外资源不接管
  if (BYPASS.some((re) => re.test(url.pathname))) return;       // APK / 版本文件直连

  // 页面导航：网络优先
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put('/', copy)).catch(() => {});
          return res;
        })
        .catch(() => caches.match('/'))
    );
    return;
  }

  // 其它资源：缓存优先
  event.respondWith(
    caches.match(req).then((hit) => {
      if (hit) return hit;
      return fetch(req).then((res) => {
        if (res && res.status === 200 && res.type === 'basic') {
          const copy = res.clone();
          caches.open(CACHE).then((c) => c.put(req, copy)).catch(() => {});
        }
        return res;
      });
    })
  );
});
