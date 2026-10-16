#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面看一遍现状：仓库、构建、线上站点。

用于判断「进行到哪一步了、哪里卡住了」。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nethelper import get, get_json  # noqa: E402

REPO = "chenguangnanlove-glitch/nan-tuner"
API = f"https://api.github.com/repos/{REPO}"
SITE = "https://nan-tuner.cc"

H = {"Accept": "application/vnd.github+json"}


def sep(t):
    print()
    print(f"\033[1m{t}\033[0m")
    print("─" * 66)


# ════════════════════════════════════════════════════════════
sep("1. 仓库代码（deploy.sh 跑过了吗）")

try:
    info = get_json(API, headers=H)
    branch = info.get("default_branch", "main")
    pushed = info.get("pushed_at", "")[:19]
    print(f"  最后推送时间：{pushed}")

    tree = get_json(f"{API}/git/trees/{branch}?recursive=1", headers=H)
    files = [t["path"] for t in tree.get("tree", []) if t.get("type") == "blob"]
    print(f"  文件总数：{len(files)}")
    print()

    checks = [
        "index.html", "archive/old-index.html",
        "web/index.html", "web/manifest.webmanifest", "web/sw.js",
        "web/app-version.json", "web/download/index.html",
        "android/app/build.gradle",
        ".github/workflows/build-apk.yml",
        "netlify.toml",
    ]
    for c in checks:
        mark = "\033[32m✓\033[0m" if c in files else "\033[31m✗\033[0m"
        print(f"    {mark} {c}")

    if "web/index.html" in files:
        print(f"\n  \033[32m→ 代码已推送成功\033[0m")
        PUSHED_OK = True
    else:
        print(f"\n  \033[33m→ 代码还没推送（仓库里还是旧版）\033[0m")
        PUSHED_OK = False

    if "web/download/shixin-tuner.apk" in files:
        print(f"  \033[32m→ APK 已经构建好了\033[0m")
except Exception as e:
    print(f"  查询失败：{e}")
    PUSHED_OK = False

# ════════════════════════════════════════════════════════════
sep("2. 自动构建记录（Actions）")

try:
    runs = get_json(f"{API}/actions/runs?per_page=5", headers=H)
    items = runs.get("workflow_runs", [])
    total = runs.get("total_count", 0)

    if total == 0:
        print("  还没有任何构建记录")
        print()
        print("  \033[33m→ 说明还没触发过构建\033[0m")
        print("     去仓库 Actions 标签 → 「构建安卓 APK」→ Run workflow")
    else:
        print(f"  共 {total} 次构建，最近 {len(items)} 次：")
        print()
        for r in items:
            status = r.get("status", "")
            concl = r.get("conclusion") or ""
            name = r.get("name", "")[:30]
            created = (r.get("created_at") or "")[:19].replace("T", " ")
            num = r.get("run_number", "")

            if concl == "success":
                icon = "\033[32m✅ 成功\033[0m"
            elif concl == "failure":
                icon = "\033[31m❌ 失败\033[0m"
            elif status == "in_progress":
                icon = "\033[33m⏳ 进行中\033[0m"
            elif status == "queued":
                icon = "\033[33m⏸  排队中\033[0m"
            else:
                icon = f"{concl or status}"

            print(f"    #{num}  {icon}  {created}")
            print(f"         {name}")
            print(f"         {r.get('html_url')}")
            print()
except Exception as e:
    print(f"  查询失败：{e}")

# ════════════════════════════════════════════════════════════
sep("3. 线上站点")

for path, label in [
    ("/", "首页"),
    ("/manifest.webmanifest", "PWA 清单"),
    ("/app-version.json", "版本信息"),
    ("/download/", "下载页"),
    ("/download/shixin-tuner.apk", "APK 安装包"),
]:
    try:
        status, headers, body = get(SITE + path, timeout=12)
        ctype = (headers.get("Content-Type") or "").split(";")[0]
        print(f"  \033[32m✓\033[0m {label:<12} {status}  {ctype:<32} {len(body):>9,} B")
    except Exception as e:
        msg = str(e)
        code = "404" if "404" in msg else "失败"
        print(f"  \033[33m·\033[0m {label:<12} {code}")

# ════════════════════════════════════════════════════════════
sep("4. 结论")

print()
if not PUSHED_OK:
    print("  当前卡在：\033[1m代码还没推送到 GitHub\033[0m")
    print()
    print("  下一步命令：")
    print("    cd ~/Desktop/始信调音器App && bash tools/deploy.sh")
elif PUSHED_OK:
    try:
        runs2 = get_json(f"{API}/actions/runs?per_page=1", headers=H)
        if runs2.get("total_count", 0) == 0:
            print("  当前卡在：\033[1m还没触发构建\033[0m")
            print()
            print("  下一步：仓库 → Actions → 构建安卓 APK → Run workflow")
        else:
            last = runs2["workflow_runs"][0]
            concl = last.get("conclusion")
            if concl == "success":
                print("  \033[32m构建成功！\033[0m")
                print()
                print("  下一步：确认 Netlify 的 Publish directory 是 web")
            elif concl == "failure":
                print("  \033[31m最近一次构建失败了\033[0m")
                print()
                print(f"  打开这个看报错：{last.get('html_url')}")
            else:
                print(f"  最近一次构建：{concl or last.get('status')}")
    except Exception:
        pass

print()
