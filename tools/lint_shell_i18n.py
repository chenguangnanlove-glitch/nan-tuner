#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
排查 shell 脚本里「$VAR 后面紧跟中文字符」的隐患。

bash 解析 $VAR 时，如果后面直接跟非 ASCII 字符（比如中文逗号），
在某些 locale 下会把那些字节当成变量名的一部分，导致
"unbound variable" 报错。

正确写法：用 ${VAR} 明确边界。

用法：python3 tools/lint_shell_i18n.py
"""

import os
import re
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

# $VAR 或 $VAR 后面紧跟非 ASCII 字符（排除 ${VAR} 的写法）
PATTERN = re.compile(r"\$(?!\{)([A-Za-z_][A-Za-z0-9_]*)([^\x00-\x7F])")

problems = 0
scanned = 0

for dirpath, dirnames, filenames in os.walk(BASE):
    dirnames[:] = [d for d in dirnames if d not in (".git", "build", ".gradle", "node_modules")]
    for fn in filenames:
        if not (fn.endswith(".sh") or fn.endswith(".bash") or fn.endswith(".command")):
            continue
        path = os.path.join(dirpath, fn)
        rel = os.path.relpath(path, BASE)
        scanned += 1

        with open(path, encoding="utf-8") as f:
            lines = f.readlines()

        found = []
        for i, line in enumerate(lines, 1):
            # 跳过注释行（但注释里的也顺手提示）
            for m in PATTERN.finditer(line):
                var, nxt = m.group(1), m.group(2)
                found.append((i, var, nxt, line.rstrip()))

        if found:
            print(f"\n\033[31m✗ {rel}\033[0m  ({len(found)} 处)")
            for lineno, var, nxt, text in found:
                print(f"    第 {lineno} 行：${var} 后面紧跟 {nxt!r}")
                print(f"      {text.strip()[:88]}")
                print(f"      \033[32m应改为：${{{var}}}{nxt}\033[0m")
            problems += len(found)
        else:
            print(f"\033[32m✓\033[0m {rel}")

print()
print("═" * 62)
if problems:
    print(f"\033[31m发现 {problems} 处隐患（共扫描 {scanned} 个脚本）\033[0m")
else:
    print(f"\033[32m✅ 全部安全（共扫描 {scanned} 个脚本）\033[0m")
print("═" * 62)

sys.exit(1 if problems else 0)
