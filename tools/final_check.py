#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上线终检：确认 APK 真的可用。

检查项：
  1. APK 能下载，且是有效的 ZIP（APK 本质是 ZIP）
  2. 里面确实有 AndroidManifest.xml 和 classes.dex
  3. 下载页面的内容正常
  4. PWA 文件齐全
"""

import io
import os
import re
import sys
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nethelper import get, get_json  # noqa: E402

SITE = "https://nan-tuner.cc"

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"


def sep(t):
    print()
    print(f"{BOLD}{t}{RESET}")
    print("─" * 70)


print()
print(f"{BOLD}上线终检{RESET}")
print("═" * 70)

# ════════════════════════════════════════════════════════════
sep("1. 下载 APK")

try:
    status, headers, data = get(f"{SITE}/download/shixin-tuner.apk", timeout=90)
    print(f"  HTTP {status}")
    print(f"  大小：{len(data):,} 字节（{len(data) / 1024 / 1024:.2f} MB）")
    print(f"  类型：{headers.get('Content-Type')}")
    cd = headers.get("Content-Disposition") or ""
    if "attachment" in cd.lower():
        print(f"  下载行为：{GREEN}✓ 强制下载{RESET}（手机不会在浏览器里打开它）")
    else:
        print(f"  {YELLOW}!{RESET} 未声明 attachment：{cd}")

    # 保存一份
    out = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                       "web", "download", "shixin-tuner.apk")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with open(out, "wb") as f:
        f.write(data)
    print(f"  已保存到：{out}")
    APK_OK = True
except Exception as e:
    print(f"  {RED}✗ 下载失败：{type(e).__name__}: {e}{RESET}")
    APK_OK = False

# ════════════════════════════════════════════════════════════
if APK_OK:
    sep("2. APK 结构校验")

    try:
        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()
        print(f"  是有效的 ZIP/APK，含 {len(names)} 个条目")
        print()

        REQUIRED = [
            ("AndroidManifest.xml", "应用清单（包名、权限、图标入口）"),
            ("classes.dex", "编译后的代码"),
            ("resources.arsc", "资源索引"),
        ]
        for path, desc in REQUIRED:
            hit = path in names
            mark = f"{GREEN}✓{RESET}" if hit else f"{RED}✗{RESET}"
            print(f"  {mark} {path:<28} {DIM}{desc}{RESET}")

        print()
        print("  签名：")
        # v1 签名在 META-INF 里，v2/v3 签名在 ZIP 中央目录前的签名区块里。
        # Android 7+ 的构建默认只用 v2+，所以只看 META-INF 会误判。
        v1 = [n for n in names if n.startswith("META-INF/") and
              n.endswith((".RSA", ".DSA", ".EC", ".SF"))]
        magic = data[-1_100_000:].find(b"APK Sig Block 42")
        if magic >= 0:
            print(f"    {GREEN}✓{RESET} v2/v3 签名区块存在（Android 7+ 使用）")
            print(f"    → {GREEN}APK 已签名，可以安装{RESET}")
        if v1:
            for v in sorted(v1):
                print(f"    {GREEN}✓{RESET} {v}（v1 签名）")
        if magic < 0 and not v1:
            print(f"    {RED}✗ 没找到任何签名{RESET}")

        print()
        print("  图标资源：")
        # AGP 会重命名资源以减小体积，所以图标不一定叫 ic_launcher
        icons = [n for n in names if "ic_launcher" in n or
                 (n.startswith("res/") and n.endswith(".png") and
                  zf.getinfo(n).file_size > 8000)]
        if icons:
            for i in sorted(icons)[:8]:
                size_i = zf.getinfo(i).file_size
                print(f"    ✓ {i}  ({size_i:,} B)")
        else:
            print(f"    {YELLOW}!{RESET} 没找到图标资源（可能被重命名了）")

        print()
        print("  内置离线页：")
        offline = [n for n in names if "offline" in n.lower()]
        for o in offline:
            print(f"    {GREEN}✓{RESET} {o}  ({zf.getinfo(o).file_size:,} B)")
        if not offline:
            print(f"    {YELLOW}!{RESET} 没找到离线页")

        # 大小分析
        print()
        print("  体积构成（最大的几个）：")
        entries = sorted(
            [(n, zf.getinfo(n).file_size) for n in names if not n.endswith("/")],
            key=lambda x: -x[1]
        )[:6]
        for n, s in entries:
            print(f"    {s:>10,} B  {n}")

    except zipfile.BadZipFile:
        print(f"  {RED}✗ 不是有效的 APK（ZIP 解析失败）{RESET}")

# ════════════════════════════════════════════════════════════
sep("3. 下载页")

try:
    status, headers, body = get(f"{SITE}/download/", timeout=20)
    html = body.decode("utf-8", errors="replace")
    print(f"  HTTP {status}  {len(html):,} 字符")

    checks = [
        ("下载按钮", 'href="/download/shixin-tuner.apk"'),
        ("图标", "/icons/icon-192.png"),
        ("iPhone 提示", "iPhone"),
        ("安装步骤", "未知来源"),
    ]
    for name, marker in checks:
        mark = f"{GREEN}✓{RESET}" if marker in html else f"{RED}✗{RESET}"
        print(f"  {mark} {name}")

    ver = re.search(r'版本 [\d.]+（\d+）· 安卓', html)
    if ver:
        print(f"  {DIM}页面上会显示：{ver.group(0)}{RESET}")
    else:
        v2 = re.search(r"安卓 [\d.]+ 及以上", html)
        if v2:
            print(f"  {DIM}页面上会显示：{v2.group(0)}{RESET}")

except Exception as e:
    print(f"  {RED}✗ {e}{RESET}")

# ════════════════════════════════════════════════════════════
sep("4. 版本信息")

try:
    v = get_json(f"{SITE}/app-version.json", timeout=15)
    print(f"  versionCode : {v.get('versionCode')}")
    print(f"  versionName : {v.get('versionName')}")
    print(f"  apk 路径    : {v.get('apk')}")
    notes = (v.get("notes") or "")[:60]
    print(f"  说明        : {notes}…")
except Exception as e:
    print(f"  {RED}✗ {e}{RESET}")

# ════════════════════════════════════════════════════════════
sep("5. 首页（是否是新版）")

try:
    status, headers, body = get(SITE, timeout=20)
    html = body.decode("utf-8", errors="replace")
    print(f"  HTTP {status}  {len(html):,} 字符")

    pwa = [
        ("PWA 清单引用", 'rel="manifest"'),
        ("下载入口", 'id="appRow"'),
        ("Service Worker", "serviceWorker.register"),
        ("App 环境检测", "ShixinApp"),
    ]
    for name, marker in pwa:
        mark = f"{GREEN}✓{RESET}" if marker in html else f"{RED}✗{RESET}"
        print(f"  {mark} {name}")

    # 调音功能还在吗
    print()
    core = {
        "音高检测": "detectPitch",
        "麦克风": "getUserMedia",
        "频闪": "strobeCanvas",
        "钢琴模式": 'data-mode="piano"',
    }
    for name, marker in core.items():
        mark = f"{GREEN}✓{RESET}" if marker in html else f"{RED}✗{RESET}"
        print(f"  {mark} {name}")

except Exception as e:
    print(f"  {RED}✗ {e}{RESET}")

# ════════════════════════════════════════════════════════════
print()
print("═" * 70)
print(f"{GREEN}{BOLD}✅ 终检完成{RESET}")
print()
print(f"  {BOLD}手机上这样装：{RESET}")
print(f"    1. 用手机浏览器打开  {SITE}/download/")
print(f"    2. 点「下载安卓版 App」")
print(f"    3. 下载完点开那个文件，允许「未知来源」安装")
print(f"    4. 桌面出现「始信音乐」图标")
print()
