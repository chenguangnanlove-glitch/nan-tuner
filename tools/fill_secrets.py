#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
GitHub Secrets 填写助手（改进版）

把 Name 和 Secret 值都自动复制到剪贴板，你只需按顺序粘贴两次。

这样就不会出现「Name 里混进空格或中文」的问题 —— 那正是
"Secret names can only contain alphanumeric characters" 报错的原因。

用法：
    python3 tools/fill_secrets.py
"""

import os
import re
import subprocess
import sys
import time

HERE = os.path.dirname(os.path.abspath(__file__))
KS_DIR = os.path.join(HERE, "keystore")
INFO_FILE = os.path.join(KS_DIR, "密钥信息.txt")
B64_FILE = os.path.join(KS_DIR, "KEYSTORE_BASE64.txt")

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
CYAN = "\033[36m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def clipboard_copy(text: str) -> bool:
    try:
        p = subprocess.run(["pbcopy"], input=text.encode("utf-8"),
                           stderr=subprocess.PIPE)
        return p.returncode == 0
    except Exception:
        return False


def read_info() -> dict:
    if not os.path.isfile(INFO_FILE):
        return {}
    with open(INFO_FILE, encoding="utf-8") as f:
        text = f.read()

    out = {}
    for key, pat in {
        "KEYSTORE_PASSWORD": r"密钥库密码\s*[：:]\s*(\S+)",
        "KEY_PASSWORD": r"密钥密码\s*[：:]\s*(\S+)",
        "KEY_ALIAS": r"密钥别名\s*[：:]\s*(\S+)",
    }.items():
        m = re.search(pat, text)
        if m:
            out[key] = m.group(1).strip()

    if os.path.isfile(B64_FILE):
        with open(B64_FILE, encoding="utf-8") as f:
            out["KEYSTORE_BASE64"] = f.read().strip()

    return out


def mask(value: str) -> str:
    if not value:
        return "（空）"
    if len(value) <= 8:
        return "*" * len(value)
    return f"{value[:3]}{'*' * 12}{value[-3:]}  （{len(value)} 字符）"


def pause(prompt="        按回车继续 "):
    try:
        return input(prompt).strip().lower()
    except (EOFError, KeyboardInterrupt):
        print()
        raise KeyboardInterrupt


def main():
    print()
    print(f"{BOLD}GitHub Secrets 填写助手{RESET}")
    print(f"{DIM}Name 和值都自动复制，你只管粘贴{RESET}")
    print()

    if not os.path.isdir(KS_DIR):
        print(f"{RED}✗ 找不到密钥目录{RESET}")
        return 1

    values = read_info()
    missing = [k for k in ("KEYSTORE_BASE64", "KEYSTORE_PASSWORD",
                           "KEY_PASSWORD", "KEY_ALIAS") if not values.get(k)]
    if missing:
        print(f"{RED}✗ 密钥信息不完整，缺少：{', '.join(missing)}{RESET}")
        return 1

    items = [
        ("KEYSTORE_BASE64", "密钥库文件的编码内容", "长内容，一大段"),
        ("KEYSTORE_PASSWORD", "密钥库密码", ""),
        ("KEY_PASSWORD", "密钥密码（和上面一样）", ""),
        ("KEY_ALIAS", "密钥别名", ""),
    ]

    # 开始前清空剪贴板，避免粘到之前残留的东西
    clipboard_copy("")

    print(f"{BOLD}先在浏览器打开这个页面：{RESET}")
    print(f"  {CYAN}仓库 → Settings → Secrets and variables → Actions{RESET}")
    print()
    print(f"{DIM}  确认页面顶部选中的是「Repository secrets」那一栏{RESET}")
    print(f"{DIM}  然后每一项都点一次「New repository secret」{RESET}")
    print()
    print("─" * 62)

    done = 0
    i = 0
    while i < len(items):
        key, desc, note = items[i]
        value = values[key]

        print()
        print(f"{BOLD}[{i + 1}/{len(items)}] {desc}{RESET}")
        if note:
            print(f"{DIM}        {note}{RESET}")
        print()

        # ---------- 第一步：复制 Name ----------
        clipboard_copy(key)
        time.sleep(0.15)
        print(f"  {BOLD}① Name 框{RESET}")
        print(f"     {GREEN}已复制：{RESET}{CYAN}{key}{RESET}")
        print(f"     {DIM}去 GitHub 点「New repository secret」，")
        print(f"     在 Name 框按 ⌘V 粘贴{RESET}")

        ans = pause()
        if ans == "q":
            print(f"\n{DIM}已退出。重新运行可继续。{RESET}")
            break
        if ans == "s":
            print(f"    {YELLOW}已跳过{RESET}")
            i += 1
            continue

        # ---------- 第二步：复制值 ----------
        print()
        print(f"  {BOLD}② Secret 框{RESET}")
        clipboard_copy(value)
        time.sleep(0.15)
        print(f"     {GREEN}已复制：{RESET}{mask(value)}")
        print(f"     {DIM}在同一页面的 Secret 框按 ⌘V，")
        print(f"     然后点绿色的「Add secret」按钮{RESET}")

        ans = pause("        填好后按回车继续 ")
        if ans == "q":
            print(f"\n{DIM}已退出。重新运行可继续。{RESET}")
            break

        print(f"  {GREEN}✓ 完成{RESET}  {DIM}（共 {i + 1} 项）{RESET}")
        done += 1
        i += 1

    print()
    print("─" * 62)
    print()
    print(f"{BOLD}本次完成：{done} 项{RESET}")
    print()

    if done == len(items):
        print(f"{GREEN}{BOLD}✅ 4 个都填好了{RESET}")
        print()
        print(f"{BOLD}下一步：触发构建{RESET}")
        print(f"  1. 打开仓库的 {CYAN}Actions{RESET} 标签")
        print(f"  2. 左侧点 {CYAN}构建安卓 APK{RESET}")
        print(f"  3. 右边点 {CYAN}Run workflow{RESET} → 绿色按钮")
        print(f"  4. 等 3–5 分钟")
        print()
    else:
        print(f"{DIM}没填完的话重新运行：python3 tools/fill_secrets.py{RESET}")
        print()

    return 0


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        print()
        print("已中断。")
        raise SystemExit(130)
