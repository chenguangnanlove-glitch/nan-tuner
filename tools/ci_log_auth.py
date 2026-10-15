#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用你钥匙串里的通行证，读取 GitHub Actions 的构建日志。

只读取，不修改任何东西。通行证不会显示出来。
"""

import io
import json
import os
import re
import subprocess
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nethelper import ssl_context, get_json  # noqa: E402

REPO = "chenguangnanlove-glitch/nan-tuner"
API = f"https://api.github.com/repos/{REPO}"


def get_token():
    """从 macOS 钥匙串读取 GitHub 通行证。"""
    try:
        p = subprocess.run(
            ["git", "credential-osxkeychain", "get"],
            input=b"protocol=https\nhost=github.com\n\n",
            capture_output=True, timeout=15,
        )
        for line in p.stdout.decode("utf-8", errors="replace").splitlines():
            if line.startswith("password="):
                return line.split("=", 1)[1].strip()
    except Exception:
        pass
    return None


def sep(t):
    print()
    print(f"\033[1m{t}\033[0m")
    print("─" * 68)


token = get_token()

if not token:
    print()
    print("  读不到通行证。请先双击「① 双击我部署」登录一次。")
    print()
    sys.exit(1)

print()
print(f"  已读到通行证：{token[:4]}****{token[-4:]}（不会显示完整内容）")

H = {
    "Accept": "application/vnd.github+json",
    "Authorization": f"token {token}",
}

# ── 找最近一次失败的构建 ──
runs = get_json(f"{API}/actions/runs?per_page=3", headers=H)
run_id = None
for r in runs.get("workflow_runs", []):
    if r.get("conclusion") == "failure":
        run_id = r["id"]
        break

if not run_id:
    print("\n  没有失败的构建，或者你不止一个仓库。")
    sys.exit(0)

sep(f"拉取构建日志 #{run_id}")

try:
    url = f"{API}/actions/runs/{run_id}/logs"
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Authorization": f"token {token}"})
    with urllib.request.urlopen(req, timeout=90, context=ssl_context()) as r:
        data = r.read()
except Exception as e:
    print(f"  下载失败：{type(e).__name__}: {e}")
    sys.exit(1)

zf = zipfile.ZipFile(io.BytesIO(data))

# 找「构建 release APK」那个日志
target = None
for n in zf.namelist():
    if "构建_release_APK" in n or "release_APK" in n or "APK" in n:
        target = n
        break
if not target:
    target = max(zf.namelist(), key=lambda n: zf.getinfo(n).file_size)

content = zf.read(target).decode("utf-8", errors="replace")

sep("失败步骤的完整日志")

# 去掉时间戳
lines = []
for line in content.splitlines():
    m = re.match(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s?", line)
    if m:
        line = line[m.end():]
    lines.append(line)

# 打印
for line in lines:
    print(f"  {line}")

# ── 提炼关键错误 ──
sep("关键错误")

KEYWORDS = [
    "error:", "Error:", "ERROR", "FAILURE", "FAILED",
    "What went wrong", "Caused by", "Could not",
    "Execution failed", "> Task", "BUILD FAILED",
    "Unresolved", "not found", "Deprecated",
]

found = []
for i, line in enumerate(lines):
    for kw in KEYWORDS:
        if kw in line:
            # 抓取上下文
            ctx = lines[max(0, i - 1):min(len(lines), i + 3)]
            found.append("\n".join(ctx))
            break

if found:
    seen = set()
    for block in found[:6]:
        if block not in seen:
            seen.add(block)
            print("  " + block.replace("\n", "\n  "))
            print("  " + "·" * 40)
else:
    print("  （没匹配到常见错误关键词，看上面的完整日志）")

print()
