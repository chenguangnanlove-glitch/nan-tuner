#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
预览专用服务器 —— 保证每次都是最新内容。

为什么不用 python -m http.server：
  1. 网页里注册了 Service Worker，它会缓存页面，
     一旦缓存过，改了文件也可能看到旧的
  2. 浏览器自身的 HTTP 缓存也会干扰

这个服务器做两件事：
  · 对 /sw.js 返回一个「自我注销」的脚本 —— 让浏览器卸掉旧缓存
  · 对所有响应加 no-store 头 —— 彻底禁用缓存

结果：改完文件刷新一下，必定看到最新效果。

用法：
    python3 tools/preview_server.py [端口]
"""

import atexit
import os
import signal
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB_DIR = os.path.join(BASE, "web")
PID_FILE = "/tmp/shixin-preview.pid"


def cleanup_pid_file():
    """退出时删掉记录文件。"""
    try:
        if os.path.isfile(PID_FILE):
            with open(PID_FILE) as f:
                if f.read().strip() == str(os.getpid()):
                    os.remove(PID_FILE)
    except Exception:
        pass


def kill_old_preview():
    """把上一次没关干净的预览服务杀掉。

    只杀自己记录过的 PID，而且验证命令行确实是 preview_server，
    不会误伤其它 Python 进程。
    """
    if not os.path.isfile(PID_FILE):
        return False
    try:
        with open(PID_FILE) as f:
            old_pid = int(f.read().strip())
    except Exception:
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
        return False

    # 先看这个进程还在不在
    try:
        os.kill(old_pid, 0)
    except ProcessLookupError:
        # 已经退出了，清掉记录
        try:
            os.remove(PID_FILE)
        except Exception:
            pass
        return False
    except PermissionError:
        # 存在但不是我们的，不动它
        return False

    # 确认它确实是预览服务（防止 PID 被复用）
    try:
        import subprocess
        r = subprocess.run(
            ["ps", "-p", str(old_pid), "-o", "command="],
            capture_output=True, text=True, timeout=5,
        )
        cmdline = r.stdout.strip()
        if "preview_server" not in cmdline:
            try:
                os.remove(PID_FILE)
            except Exception:
                pass
            return False
    except Exception:
        return False

    # 确认无误，杀掉
    try:
        os.kill(old_pid, signal.SIGTERM)
        import time
        time.sleep(0.6)
        os.kill(old_pid, signal.SIGKILL)
    except Exception:
        pass

    try:
        os.remove(PID_FILE)
    except Exception:
        pass
    return True

# 让浏览器把已经注册的 Service Worker 卸掉，并清空它的缓存。
# 这样预览环境永远拿网络上的最新文件。
#
# 注意：不能用 client.navigate() —— Chrome 不支持这个 API。
# 改用 postMessage 通知页面自行刷新（页面收到后 reload），
# 或者让用户手动刷新一次。
KILL_SW = """/* 预览模式：停用 Service Worker，清空缓存 */
self.addEventListener('install', () => self.skipWaiting());

self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys()
      .then((keys) => Promise.all(keys.map((k) => caches.delete(k))))
      .then(() => self.registration.unregister())
      .then(() => self.clients.matchAll({ type: 'window' }))
      .then((clients) => {
        // 通知每个页面：缓存清完了，可以刷新了
        clients.forEach((c) => {
          try { c.postMessage({ type: 'preview-cache-cleared' }); } catch (e) {}
        });
      })
      .catch(() => {})
  );
});

// 不拦截任何请求，全部走网络
"""


class PreviewHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def end_headers(self):
        # 禁用一切缓存
        self.send_header("Cache-Control", "no-store, no-cache, must-revalidate, max-age=0")
        self.send_header("Pragma", "no-cache")
        self.send_header("Expires", "0")
        super().end_headers()

    def send_html_without_sw(self, path):
        """返回 HTML，但把 Service Worker 注册那行去掉。

        为什么：预览环境下不需要 SW，它反而会缓存页面导致看不到最新改动。
        只在确实匹配到时才替换，匹配不到就原样返回，不会搞坏内容。
        """
        try:
            with open(path, "rb") as f:
                data = f.read()
        except OSError:
            self.send_error(404)
            return

        text = data.decode("utf-8", errors="replace")
        original = text

        # 把注册 SW 的那段换成什么都不做的 Promise。
        # 不能用 void 0 —— 后面还跟着 .catch(...)，
        # undefined.catch 会抛类型错误。用 Promise.resolve() 最干净。
        text = text.replace(
            "navigator.serviceWorker.register('/sw.js')",
            "Promise.resolve() /* 预览模式：不注册 Service Worker */",
        )

        if text != original:
            sys.stderr.write("  （已为该页面禁用 Service Worker）\n")

        body = text.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        path = self.path.split("?")[0]

        # 拦截 Service Worker，返回注销脚本
        if path == "/sw.js":
            body = KILL_SW.encode("utf-8")
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
            return

        # HTML 页面：去掉 SW 注册
        if path in ("/", "/index.html"):
            self.send_html_without_sw(os.path.join(WEB_DIR, "index.html"))
            return

        super().do_GET()

    def log_message(self, fmt, *args):
        # 安静一点，只记录错误
        if args and str(args[1]).startswith(("4", "5")):
            sys.stderr.write("  %s\n" % (fmt % args))


def main():
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8123

    if not os.path.isdir(WEB_DIR):
        print(f"找不到目录：{WEB_DIR}")
        sys.exit(1)

    # 先清掉上次残留的预览服务
    if kill_old_preview():
        print("（已清理上一次残留的预览服务）")

    # 找一个空闲端口（被占就往后找，而不是失败）
    httpd = None
    chosen = None
    for p in range(port, port + 60):
        try:
            httpd = ThreadingHTTPServer(("127.0.0.1", p), PreviewHandler)
            chosen = p
            break
        except OSError:
            continue

    if httpd is None:
        print(f"端口 {port}–{port + 59} 都被占用了")
        print("请在「活动监视器」里结束旧的 Python 进程，或重启电脑。")
        sys.exit(1)

    # 记下自己的 PID，方便下次清理
    try:
        with open(PID_FILE, "w") as f:
            f.write(str(os.getpid()))
        atexit.register(cleanup_pid_file)
    except Exception:
        pass

    if chosen != port:
        print(f"（端口 {port} 被占用，改用 {chosen}）")

    print(f"预览服务器已启动：http://127.0.0.1:{chosen}/")
    print("按 Control + C 停止")

    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n已停止")
    finally:
        httpd.server_close()
        cleanup_pid_file()


if __name__ == "__main__":
    main()
