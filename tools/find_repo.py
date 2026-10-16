#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
找你的 GitHub 仓库 —— 通过公开搜索 API。

只用公开信息，不涉及任何私密数据。
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nethelper import get_json  # noqa: E402


def search(q, label):
    print(f"\n\033[1m{label}\033[0m")
    print("─" * 68)
    try:
        data = get_json(
            f"https://api.github.com/search/repositories?q={q}&per_page=10",
            headers={"Accept": "application/vnd.github+json"},
        )
    except Exception as e:
        print(f"  搜索失败：{e}")
        return []

    total = data.get("total_count", 0)
    items = data.get("items", [])
    print(f"  匹配 {total} 个仓库\n")

    out = []
    for it in items[:10]:
        name = it.get("full_name", "")
        desc = (it.get("description") or "")[:44]
        lang = it.get("language") or "-"
        updated = (it.get("updated_at") or "")[:10]
        stars = it.get("stargazers_count", 0)
        print(f"  {name}")
        print(f"     描述: {desc or '（无）'}")
        print(f"     语言: {lang}   更新: {updated}   ★{stars}")
        print(f"     地址: {it.get('html_url')}")
        print()
        out.append(it)
    return out


print()
print("搜索 GitHub 公开仓库")
print("═" * 68)

found = search("nan-tuner+in:name", "1. 按仓库名搜 nan-tuner")
found2 = search("nan-tuner+in:name+user:nan", "2. 限制用户名含 nan")
found3 = search("shixin+tuner+in:name", "3. 按 shixin + tuner 搜")

print("═" * 68)
if found or found2 or found3:
    print("\n  上面哪个是你的？告诉我仓库全名（用户名/仓库名）就行。")
else:
    print("\n  没搜到公开仓库。")
    print()
    print("  可能它是私有的（Private），公开搜索看不到。")
    print("  那就直接把仓库地址告诉我：")
    print("    https://github.com/你的用户名/nan-tuner")
print()
