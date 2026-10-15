#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""连通性总检查：确认各关键节点是否可达，并看线上文件状态。"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nethelper import get, ssl_context  # noqa: E402

TARGETS = [
    ("GitHub",       "https://github.com"),
    ("GitHub API",   "https://api.github.com"),
    ("Netlify API",  "https://api.netlify.com/api/v1"),
    ("你的站点",      "https://nan-tuner.cc"),
    ("下载页",        "https://nan-tuner.cc/download/"),
    ("PWA 清单",      "https://nan-tuner.cc/manifest.webmanifest"),
    ("版本信息",      "https://nan-tuner.cc/app-version.json"),
    ("图标 192",      "https://nan-tuner.cc/icons/icon-192.png"),
    ("Service Worker", "https://nan-tuner.cc/sw.js"),
]

print()
print("连通性检查")
print("─" * 66)

ok_count = 0
for name, url in TARGETS:
    try:
        status, headers, body = get(url, timeout=15)
        ctype = (headers.get("Content-Type") or "").split(";")[0]
        size = len(body)
        print(f"  \033[32m✓\033[0m {name:<15} HTTP {status}  {ctype:<30} {size:>9,} B")
        ok_count += 1
    except Exception as e:
        short = f"{type(e).__name__}"
        if "CERTIFICATE" in str(e):
            short = "证书验证失败"
        print(f"  \033[31m✗\033[0m {name:<15} {short}: {str(e)[:50]}")

print("─" * 66)
print(f"  {ok_count}/{len(TARGETS)} 可达")
