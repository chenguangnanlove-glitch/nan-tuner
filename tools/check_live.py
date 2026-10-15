#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
线上现状全面检查 —— 一次跑完，把该看的都看了。

检查内容：
  1. nan-tuner.cc 是否正常、有哪些文件
  2. 找到你现在的网页版调音器长什么样
  3. 从响应头里找 GitHub 仓库的线索
  4. 判断线上有没有 PWA 相关文件
"""

import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nethelper import get  # noqa: E402

SITE = "https://nan-tuner.cc"

# 你可能会部署的文件
PROBES = [
    "/",
    "/index.html",
    "/manifest.webmanifest",
    "/sw.js",
    "/app-version.json",
    "/download/",
    "/download/shixin-tuner.apk",
    "/icons/icon-192.png",
    "/netlify.toml",
    "/robots.txt",
    "/404.html",
]


def sep(title):
    print()
    print(f"\033[1m{title}\033[0m")
    print("─" * 68)


sep("1. 线上文件清单")

results = {}
for path in PROBES:
    url = SITE + path
    try:
        status, headers, body = get(url, timeout=15)
        ctype = (headers.get("Content-Type") or "").split(";")[0]
        results[path] = (status, headers, body)
        print(f"  \033[32m✓\033[0m {path:<32} {status}  {ctype:<28} {len(body):>9,} B")
    except Exception as e:
        code = ""
        msg = str(e)
        m = re.search(r"\b(4\d\d|5\d\d)\b", msg)
        if m:
            code = m.group(1)
        results[path] = None
        print(f"  \033[33m·\033[0m {path:<32} {code or '失败'}  {msg[:36]}")

sep("2. 部署平台与缓存策略")

if results.get("/"):
    _, h, body = results["/"]
    interesting = [
        "server", "x-nf-request-id", "cache-control", "content-type",
        "x-served-by", "via", "age", "etag", "last-modified",
        "permissions-policy", "strict-transport-security",
    ]
    for k in interesting:
        v = h.get(k) or h.get(k.title())
        if v:
            print(f"  {k:<28} {str(v)[:52]}")

    if h.get("x-nf-request-id") or "netlify" in str(h.get("server", "")).lower():
        print(f"\n  \033[32m→ 部署平台：Netlify\033[0m")

sep("3. 首页内容")

if results.get("/") or results.get("/index.html"):
    key = "/" if results.get("/") else "/index.html"
    _, h, body = results[key]
    text = body.decode("utf-8", errors="replace")

    title = re.search(r"<title>(.*?)</title>", text, re.S)
    print(f"  标题     : {title.group(1).strip() if title else '（无）'}")
    print(f"  大小     : {len(text):,} 字符")

    # 判断是不是调音器
    markers = {
        "音高检测": "detectPitch",
        "麦克风采集": "getUserMedia",
        "频闪视图": "strobeCanvas",
        "音名显示": "noteName",
        "指针显示": "noteName",
        "钢琴模式": 'data-mode="piano"',
        "尤克里里": 'data-mode="ukulele"',
    }
    hit = [k for k, v in markers.items() if v in text]
    print(f"  调音功能 : {', '.join(hit) if hit else '（没检测到）'}")

    # PWA 相关
    pwa = {
        "manifest 链接": 'rel="manifest"',
        "图标引用": "/icons/",
        "Service Worker": "serviceWorker",
        "下载入口": "appRow",
    }
    pwa_hit = [k for k, v in pwa.items() if v in text]
    print(f"  PWA 支持 : {', '.join(pwa_hit) if pwa_hit else '（没有）'}")

    # 和你桌面上的源文件比大小
    src = os.path.join(os.path.dirname(os.path.dirname(
        os.path.dirname(os.path.abspath(__file__)))), "index tuner.html")
    if os.path.isfile(src):
        with open(src, encoding="utf-8") as f:
            local = f.read()
        print(f"  桌面源文件: {len(local):,} 字符")
        if abs(len(local) - len(text)) < 200:
            print(f"  \033[32m→ 线上就是你这个版本（大小几乎一致）\033[0m")
        else:
            print(f"  \033[33m→ 线上和桌面版不一致（差 {len(text) - len(local):+,} 字符）\033[0m")

sep("4. 结论")

has_ver = results.get("/app-version.json") is not None
has_manifest = results.get("/manifest.webmanifest") is not None
has_apk = results.get("/download/shixin-tuner.apk") is not None

print()
if not has_manifest and not has_ver:
    print("  \033[33m线上还是纯网页版\033[0m（没有 PWA、没有版本文件、没有 APK）")
    print()
    print("  这正是预期的状态 —— 我们做好的东西还没部署上去。")
elif has_apk:
    print("  \033[32m线上已经是完整的 App 版本了\033[0m")
else:
    print("  线上已有部分 PWA 文件，但 APK 还没就位")

print()
