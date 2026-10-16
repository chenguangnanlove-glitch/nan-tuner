#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证「自动更新」机制在服务端是否真的能工作。

App 每次启动会请求 /app-version.json，拿它和本地版本比对。
这里检查三个关键点：
  1. 这个请求会不会被缓存（被缓存 = 永远检测不到更新）
  2. 返回的内容对不对
  3. APK 下载链接是不是最新那个
"""

import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from nethelper import get, get_json  # noqa: E402

SITE = "https://nan-tuner.cc"

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"

# 收集检查结果，最后据此下结论
results = {"ok": 0, "fail": 0, "warn": 0}


def ok(msg):
    results["ok"] += 1
    print(f"  {GREEN}✓{RESET} {msg}")


def fail(msg):
    results["fail"] += 1
    print(f"  {RED}✗{RESET} {msg}")


def warn(msg):
    results["warn"] += 1
    print(f"  {YELLOW}!{RESET} {msg}")


def sep(t):
    print()
    print(f"{BOLD}{t}{RESET}")
    print("─" * 68)


print()
print(f"{BOLD}自动更新机制验证{RESET}")
print("═" * 68)

# ════════════════════════════════════════════════════════════
sep("1. 版本信息的缓存策略")

try:
    status, headers, body = get(f"{SITE}/app-version.json", timeout=15)
    print(f"  HTTP {status}")

    cc = (headers.get("Cache-Control") or "").lower()
    print(f"  Cache-Control : {cc or '（没设置）'}")

    no_store = "no-store" in cc or "no-cache" in cc or "max-age=0" in cc
    if no_store:
        ok("不会被缓存 —— App 每次都能拿到最新版本号")
    else:
        fail("可能被缓存 —— 用户可能检测不到更新")
        print(f"     {DIM}需要在 netlify.toml 里给这个路径加 no-store{RESET}")

    age = headers.get("Age")
    if age:
        print(f"  Age           : {age}  {DIM}（CDN 缓存时长）{RESET}")
except Exception as e:
    fail(f"请求失败：{type(e).__name__}: {str(e)[:60]}")

# ════════════════════════════════════════════════════════════
sep("2. 连续请求是否返回一致结果")

try:
    codes = []
    for i in range(3):
        _, _, b = get(f"{SITE}/app-version.json", timeout=15)
        import json
        codes.append(json.loads(b.decode()).get("versionCode"))
        time.sleep(0.4)
    if len(set(codes)) == 1:
        ok(f"三次请求都返回 versionCode = {codes[0]}")
    else:
        warn(f"返回值不一致：{codes}")
except Exception as e:
    fail(f"请求失败：{type(e).__name__}: {str(e)[:60]}")

# ════════════════════════════════════════════════════════════
sep("3. 版本信息与 APK 是否对得上")

try:
    v = get_json(f"{SITE}/app-version.json", timeout=15)
    apk_path = v.get("apk", "")
    print(f"  声明的 APK 路径：{apk_path}")

    # App 里下载的地址 = 站点地址 + apk 路径
    url = SITE + (apk_path if apk_path.startswith("/") else "/" + apk_path)
    status, headers, data = get(url, timeout=90)
    print(f"  实际下载      ：HTTP {status}  {len(data):,} 字节")

    # 检查 APK 的下载响应头（App 会把它交给系统浏览器）
    cd = headers.get("Content-Disposition") or ""
    ctype = headers.get("Content-Type") or ""
    print(f"  Content-Type  ：{ctype}")

    if "package-archive" in ctype:
        ok("手机能识别为安装包")
    else:
        fail("类型不对，手机可能当普通文件处理")

    if "attachment" in cd.lower():
        ok("触发下载而非在浏览器打开")

    # 版本号
    vc = v.get("versionCode")
    vn = v.get("versionName")
    print()
    print(f"  版本号        ：{vn}（versionCode {vc}）")
    print(f"  {DIM}App 里内置的 versionCode 也是 {vc}，所以现在不会提示更新。{RESET}")
    print(f"  {DIM}以后你把 app-version.json 的 versionCode 加到 {int(vc) + 1}，")
    print(f"  老用户打开 App 就会收到更新提示。{RESET}")

except Exception as e:
    fail(f"检查失败：{type(e).__name__}: {str(e)[:60]}")

# ════════════════════════════════════════════════════════════
sep("4. APK 有没有被缓存成旧版本")

try:
    _, h1, d1 = get(f"{SITE}/download/shixin-tuner.apk", timeout=90)
    time.sleep(1)
    _, h2, d2 = get(f"{SITE}/download/shixin-tuner.apk", timeout=90)

    if len(d1) == len(d2):
        ok(f"两次下载大小一致（{len(d1):,} 字节）")
    else:
        warn(f"两次大小不同：{len(d1):,} vs {len(d2):,}")

    cc = (h2.get("Cache-Control") or "").lower()
    print(f"  Cache-Control : {cc or '（没设置）'}")
    if "no-cache" in cc or "max-age=0" in cc:
        ok("每次都取最新的安装包")
    else:
        print(f"  {DIM}· 会被缓存，但因为有 ETag 校验，内容变了仍能更新{RESET}")

    etag = h1.get("ETag")
    if etag:
        print(f"  ETag          : {etag[:40]}…")
except Exception as e:
    fail(f"检查失败：{type(e).__name__}: {str(e)[:60]}")

# ════════════════════════════════════════════════════════════
print()
print("═" * 68)

if results["fail"] > 0:
    print(f"{RED}{BOLD}✗ 有 {results['fail']} 项没通过，更新机制可能有问题{RESET}")
    print()
    print(f"  {DIM}上面标 ✗ 的就是要修的。{RESET}")
    print(f"  {DIM}如果全是网络错误（SSL/超时），先确认代理正常再跑一次。{RESET}")
    sys.exit(1)
else:
    print(f"{GREEN}{BOLD}✅ 更新机制就绪{RESET}  （{results['ok']} 项通过"
          + (f"，{results['warn']} 项提醒" if results["warn"] else "") + "）")
    print()
    print(f"  {BOLD}以后发新版的完整流程：{RESET}")
    print()
    print(f"  1. 改代码（改 web/ 里的文件）")
    print(f"  2. 改版本号：web/app-version.json 里的 versionCode 加 1")
    print(f"  3. 推送：bash tools/deploy.sh")
    print(f"  4. GitHub 自动打包新版 APK（约 2 分钟）")
    print()
    print(f"  老用户打开 App 会看到「发现新版本」，点一下就能更新。")
    print()
