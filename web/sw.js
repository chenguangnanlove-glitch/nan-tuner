/* 始信音乐 · 调音器 —— Service Worker
 *
 * 策略：
 *   - 页面导航  → 网络优先（保证永远拿到最新版），断网时用缓存兜底
 *   - 音频清单  → 网络优先（audio-manifest.js 文件名不变，缓存优先会把老哈希一直留下）
 *   - 静态资源  → 缓存优先（图标等，秒开）
 *   - 音频文件  → 缓存优先（URL 带 ?v= 内容哈希，命中即最新）
 *   - APK / 版本文件 → 完全不接管，永远走网络
 *
 * 注意：改了 PRECACHE 里的资源就要改 CACHE 版本号，否则老用户拿不到新的。
 * 音频文件不靠这个 —— 它们走带内容哈希的 URL（web/audio-manifest.js），
 * 文件一变 URL 就变，缓存自然失效。清单本身没有哈希，所以单独走网络优先。
 */

const CACHE = 'shixin-tuner-v10';

const PRECACHE = [
  '/',
  '/icons/icon-192.png',
  '/icons/icon-512.png',
  '/icons/icon-maskable-512.png',
  '/icons/favicon.png',
  '/manifest.webmanifest',
  '/fonts/roboto-400.woff2',
  '/fonts/roboto-500.woff2',
  '/fonts/roboto-700.woff2'
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

/* 只把成功的响应写进缓存。用 URL 字符串做键：
   导航请求的 mode 是 navigate，直接 put(Request) 在部分浏览器里会失败，
   而且以前一律 put('/')，会把 /download/ 或错误页盖成首页。 */
function store(url, res){
  if (!res || !res.ok) return;
  const copy = res.clone();
  caches.open(CACHE).then((c) => c.put(url, copy)).catch(() => {});
}

self.addEventListener('fetch', (event) => {
  const req = event.request;
  if (req.method !== 'GET') return;

  const url = new URL(req.url);
  if (url.origin !== self.location.origin) return;              // 站外资源不接管
  if (BYPASS.some((re) => re.test(url.pathname))) return;       // APK / 版本文件直连

  // 页面导航：网络优先，按这次请求的真实 URL 缓存
  if (req.mode === 'navigate') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          store(req.url, res);
          return res;
        })
        .catch(() => caches.match(req).then((hit) => hit || caches.match('/')))
    );
    return;
  }

  // 音频清单：网络优先，失败才用缓存。
  // 采样换了只改这个文件里的哈希；若走下面的缓存优先，老用户永远要不到新音频。
  if (url.pathname === '/audio-manifest.js') {
    event.respondWith(
      fetch(req)
        .then((res) => {
          store(req.url, res);
          return res;
        })
        .catch(() => caches.match(req).then((hit) => {
          if (hit) return hit;
          return Promise.reject(new Error('audio-manifest unavailable'));
        }))
    );
    return;
  }

  // 音频：带 ?v= 内容哈希的走缓存优先
  // （URL 随文件内容变，所以命中缓存就说明是最新的，永不陈旧）
  // 不带版本的（老链接 / 清单未加载）也缓存，但下次有哈希 URL 时会另存一份
  if (/\.(m4a|mp3|ogg|wav)$/i.test(url.pathname)) {
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
