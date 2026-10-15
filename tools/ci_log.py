#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
查看 GitHub Actions 失败的构建日志。

用法：python3 tools/ci_log.py [run_id]
"""

import json
import os
import sys
import urllib.request
import zipfile
import io

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nethelper import get, get_json, ssl_context  # noqa: E402

REPO = "chenguangnanlove-glitch/nan-tuner"
API = f"https://api.github.com/repos/{REPO}"
H = {"Accept": "application/vnd.github+json"}


def sep(t):
    print()
    print(f"\033[1m{t}\033[0m")
    print("─" * 68)


# ── 找到最近一次失败 ──
run_id = sys.argv[1] if len(sys.argv) > 1 else None

if not run_id:
    runs = get_json(f"{API}/actions/runs?per_page=5", headers=H)
    for r in runs.get("workflow_runs", []):
        if r.get("conclusion") == "failure":
            run_id = r["id"]
            break
    if not run_id:
        print("最近没有失败的构建")
        sys.exit(0)

sep(f"检查构建 #{run_id}")

info = get_json(f"{API}/actions/runs/{run_id}", headers=H)
print(f"  状态    : {info.get('status')} / {info.get('conclusion')}")
print(f"  触发    : {info.get('event')}")
print(f"  分支    : {info.get('head_branch')}")
print(f"  提交    : {(info.get('head_sha') or '')[:8]}")
print(f"  创建    : {(info.get('created_at') or '')[:19]}")

# ── 各步骤状态 ──
sep("执行步骤")
jobs = get_json(f"{API}/actions/runs/{run_id}/jobs", headers=H)
failed_steps = []

for job in jobs.get("jobs", []):
    print(f"\n  任务：{job.get('name')}  →  {job.get('conclusion')}")
    for st in job.get("steps", []):
        concl = st.get("conclusion") or ""
        if concl == "success":
            icon = "\033[32m✓\033[0m"
        elif concl in ("failure", "cancelled"):
            icon = "\033[31m✗\033[0m"
        elif concl == "skipped":
            icon = "\033[2m—\033[0m"
        else:
            icon = " "
        print(f"     {icon} {st.get('name')}")
        if concl == "failure":
            failed_steps.append(st.get("name"))

# ── 下载日志 ──
sep("失败步骤的日志")

if not failed_steps:
    print("  没有失败的步骤（可能是取消或超时）")
else:
    print(f"  失败的步骤：{', '.join(failed_steps)}")
    print()

    try:
        url = f"{API}/actions/runs/{run_id}/logs"
        import urllib.request

        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60, context=ssl_context()) as r:
            data = r.read()

        zf = zipfile.ZipFile(io.BytesIO(data))
        names = zf.namelist()

        # 找到失败任务对应的日志文件
        target = None
        for n in names:
            for fs in failed_steps:
                # 日志文件名里会把空格换成下划线
                safe = fs.replace(" ", "_").replace("/", "_")
                if safe in n or fs in n:
                    target = n
                    break
            if target:
                break

        if not target:
            # 退路：取最大的那个日志
            target = max(names, key=lambda n: zf.getinfo(n).file_size)

        print(f"  日志文件：{target}")
        print()
        print("─" * 68)

        content = zf.read(target).decode("utf-8", errors="replace")
        lines = content.splitlines()

        # 只显示关键部分
        for line in lines:
            # 去掉时间戳前缀
            if line.startswith("20") and "Z " in line[:30]:
                line = line[30:]
            print(f"  {line}")

    except Exception as e:
        print(f"  读不到日志：{type(e).__name__}: {e}")
        print()
        print("  手动查看：")
        print(f"  https://github.com/{REPO}/actions/runs/{run_id}")

print()
