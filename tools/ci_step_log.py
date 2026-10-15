#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
读取指定步骤的构建日志。

用法：
    python3 tools/ci_step_log.py "提交 APK"
    python3 tools/ci_step_log.py --list         # 只列出所有日志文件
"""

import io
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


token = get_token()
if not token:
    print("读不到通行证")
    sys.exit(1)

H = {"Accept": "application/vnd.github+json", "Authorization": f"token {token}"}

# 找最近一次构建（不管成功失败）
runs = get_json(f"{API}/actions/runs?per_page=1", headers=H)
items = runs.get("workflow_runs", [])
if not items:
    print("没有构建记录")
    sys.exit(0)

run = items[0]
print(f"\n构建 #{run['run_number']}  {run.get('conclusion')}  {run.get('created_at')[:19]}")
print(f"  {run['html_url']}\n")

# 下载日志
url = f"{API}/actions/runs/{run['id']}/logs"
try:
    req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0",
                                               "Authorization": f"token {token}"})
    with urllib.request.urlopen(req, timeout=120, context=ssl_context()) as r:
        data = r.read()
except Exception as e:
    print(f"日志下载失败：{type(e).__name__}: {e}")
    sys.exit(1)

zf = zipfile.ZipFile(io.BytesIO(data))
names = zf.namelist()

print("包里的日志文件：")
for n in sorted(names):
    size = zf.getinfo(n).file_size
    print(f"  {n}  ({size:,} 字节)")

want = sys.argv[1] if len(sys.argv) > 1 and not sys.argv[1].startswith("--") else None

if "--list" in sys.argv:
    sys.exit(0)

# 选文件
target = None
if want:
    for n in names:
        safe = want.replace(" ", "_")
        if safe in n or want in n:
            target = n
            break
if not target:
    target = max(names, key=lambda n: zf.getinfo(n).file_size)

print(f"\n{'═' * 70}")
print(f"  {target}")
print(f"{'═' * 70}\n")

content = zf.read(target).decode("utf-8", errors="replace")
for line in content.splitlines():
    m = re.match(r"^\d{4}-\d{2}-\d{2}T[\d:.]+Z\s?", line)
    if m:
        line = line[m.end():]
    print(f"  {line}")
