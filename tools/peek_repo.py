#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看指定 GitHub 仓库的内容 —— 只看公开信息，不修改任何东西。

用法：
    python3 tools/peek_repo.py 用户名/仓库名
"""

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nethelper import get, get_json  # noqa: E402

REPO = sys.argv[1] if len(sys.argv) > 1 else "chenguangnanlove-glitch/nan-tuner"
API = f"https://api.github.com/repos/{REPO}"


def sep(t):
    print()
    print(f"\033[1m{t}\033[0m")
    print("─" * 68)


print(f"\n检查仓库：{REPO}")
print("═" * 68)

# ---------- 仓库概况 ----------
sep("1. 仓库概况")
try:
    info = get_json(API, headers={"Accept": "application/vnd.github+json"})
    print(f"  名称      : {info.get('full_name')}")
    print(f"  描述      : {info.get('description') or '（无）'}")
    print(f"  公开/私有 : {'公开' if not info.get('private') else '私有'}")
    print(f"  语言      : {info.get('language')}")
    print(f"  默认分支  : {info.get('default_branch')}")
    print(f"  创建时间  : {(info.get('created_at') or '')[:19]}")
    print(f"  更新时间  : {(info.get('updated_at') or '')[:19]}")
    print(f"  大小      : {info.get('size', 0)} KB")
    print(f"  主页      : {info.get('homepage') or '（未设置）'}")
    BRANCH = info.get("default_branch", "main")
except Exception as e:
    print(f"  \033[31m读不到：{e}\033[0m")
    sys.exit(1)

# ---------- 文件列表 ----------
sep("2. 文件列表")
try:
    items = get_json(f"{API}/git/trees/{BRANCH}?recursive=1",
                     headers={"Accept": "application/vnd.github+json"})
    tree = items.get("tree", [])
    files = [t for t in tree if t.get("type") == "blob"]
    dirs = sorted({os.path.dirname(t["path"]) for t in tree if t.get("type") == "tree"})

    print(f"  共 {len(files)} 个文件\n")
    for f in sorted(files, key=lambda x: x["path"])[:40]:
        print(f"    {f['path']:<52} {f.get('size', 0):>9,} B")
    if len(files) > 40:
        print(f"    …（还有 {len(files) - 40} 个）")

    if dirs:
        print(f"\n  目录：{', '.join(d for d in dirs if d)}")
except Exception as e:
    print(f"  读不到：{e}")
    files = []

# ---------- 对比线上 ----------
sep("3. 关键文件是否与线上对应")

NAMES = {f["path"] for f in files}

for path in ["index.html", "netlify.toml", "manifest.webmanifest", "sw.js",
             "app-version.json", "README.md"]:
    mark = "\033[32m有\033[0m" if path in NAMES else "\033[33m无\033[0m"
    print(f"  {path:<28} {mark}")

# ---------- 拉取 index.html 对比 ----------
sep("4. 仓库里的网页 vs 你的桌面文件")

if "index.html" in NAMES:
    try:
        raw_url = f"https://raw.githubusercontent.com/{REPO}/{BRANCH}/index.html"
        _, _, body = get(raw_url)
        repo_html = body.decode("utf-8", errors="replace")
        repo_hash = hashlib.sha256(repo_html.encode()).hexdigest()[:16]

        print(f"  仓库里的 index.html : {len(repo_html):,} 字符  sha {repo_hash}")

        src = "/Users/nan/Desktop/index tuner.html"
        if os.path.isfile(src):
            with open(src, encoding="utf-8") as f:
                local = f.read()
            local_hash = hashlib.sha256(local.encode()).hexdigest()[:16]
            print(f"  你桌面的源文件      : {len(local):,} 字符  sha {local_hash}")
            print()
            if repo_hash == local_hash:
                print("  \033[32m→ 内容完全一致（仓库里就是你桌面这个版本）\033[0m")
            elif abs(len(repo_html) - len(local)) < 50:
                print("  \033[33m→ 很接近，可能有微小改动\033[0m")
            else:
                print(f"  \033[33m→ 不一致（差 {len(repo_html) - len(local):+,} 字符）\033[0m")
    except Exception as e:
        print(f"  拉取失败：{e}")

# ---------- 结论 ----------
sep("5. 结论与建议")

has_web = "index.html" in NAMES
has_netlify = "netlify.toml" in NAMES
has_pwa = "manifest.webmanifest" in NAMES

print()
if has_web and not has_pwa:
    print("  \033[32m情况：就是纯静态网页仓库\033[0m")
    print()
    print("  \033[1m合并方案（推荐）：\033[0m")
    print("    把新文件加进去，替换 index.html。")
    print()
    print("    要新增的：")
    print("      manifest.webmanifest     PWA 清单")
    print("      sw.js                    离线缓存")
    print("      app-version.json         版本号")
    print("      icons/                   图标")
    print("      download/index.html      下载页")
    print("      android/                 安卓工程")
    print("      .github/                 自动构建")
    print("      netlify.toml             如果已有就更新")
    print()
    print("    要替换的：")
    print("      index.html               （新版功能一样，多了 PWA 支持）")
    print()
    print("    原有文件会先备份，随时能还原。")
else:
    print("  请把上面的输出发给我一起看。")

print()
print("═" * 68)
