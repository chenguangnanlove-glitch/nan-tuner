#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
交叉检查：JS 引用的所有元素 id，是否都存在于 HTML 里。

这是最容易出错的地方 —— 少一个 id 就会在浏览器里报 null 错误。
"""

import os
import re
import sys

BASE = "/Users/nan/Desktop/始信调音器App"
WEB = os.path.join(BASE, "web", "index.html")

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"

html = open(WEB, encoding="utf-8").read()

print()
print(f"{BOLD}元素 id 交叉检查{RESET}")
print("═" * 70)

# ══════════════════════════════════════════════════════════
#  1. HTML 里定义了哪些 id
# ══════════════════════════════════════════════════════════

defined = set(re.findall(r'id="([\w-]+)"', html))
print(f"\n  HTML 里定义了 {len(defined)} 个 id")

# ══════════════════════════════════════════════════════════
#  2. JS 里引用了哪些 id
# ══════════════════════════════════════════════════════════

blocks = []
for m in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S):
    blocks.append(m.group(1))

all_js = "\n".join(blocks)

# getElementById('xxx')
by_id = set(re.findall(r"""getElementById\(\s*['"]([\w-]+)['"]\s*\)""", all_js))

# querySelector('#xxx')
by_sel = set(re.findall(r"""querySelector(?:All)?\(\s*['"]#([\w-]+)['"]""", all_js))

referenced = by_id | by_sel

print(f"  JS 里引用了 {len(referenced)} 个 id")
print(f"    · getElementById: {len(by_id)} 个")
print(f"    · querySelector:  {len(by_sel)} 个")

# ══════════════════════════════════════════════════════════
#  3. 对比
# ══════════════════════════════════════════════════════════

print()
missing = sorted(referenced - defined)

if missing:
    print(f"{BOLD}检查结果{RESET}")
    print()
    print(f"  {RED}✗ 有 {len(missing)} 个 id 被引用但没定义：{RESET}")
    for m_ in missing:
        # 找出在哪一段引用的
        where = "节拍器" if m_ in ["appTabs", "tabTuner", "tabMetro", "pageMetro",
                                   "meterPresets", "numUp", "numDown", "numValue",
                                   "denUp", "denDown", "denValue", "metroRing",
                                   "pulseRing", "ringDot", "ringMeter", "beatDots",
                                   "bpmUp", "bpmDown", "bpmValue", "bpmTerm",
                                   "metroStart"] else "调音器"
        print(f"      {m_:<16} {DIM}（{where}）{RESET}")
    sys.exit(1)

print(f"  {GREEN}✓{RESET} 所有被引用的 id 都已定义")

# ══════════════════════════════════════════════════════════
#  4. 检查节拍器专用的 id
# ══════════════════════════════════════════════════════════

print()
print(f"{BOLD}节拍器元素明细{RESET}")
print()

METRO_IDS = [
    ("appTabs",      "切换键容器"),
    ("tabTuner",     "调音键"),
    ("tabMetro",     "节拍键"),
    ("pageTuner",    "调音页"),
    ("pageMetro",    "节拍页"),
    ("meterBtn",     "拍号按钮"),
    ("meterLabel",   "拍号显示"),
    ("meterSheet",   "拍号面板"),
    ("meterClose",   "面板关闭"),
    ("numGrid",      "分子网格"),
    ("denGrid",      "分母网格"),
    ("metroRing",    "圆环容器"),
    ("ringProgress", "进度弧"),
    ("pulseRing",    "脉冲环"),
    ("bpmValue",     "BPM 数字（可点）"),
    ("bpmInput",     "BPM 输入框"),
    ("bpmTerm",      "速度术语"),
    ("ringCenter",   "圆心容器"),
    ("beatDots",     "拍点容器"),
]

ok = 0
for eid, desc in METRO_IDS:
    in_html = eid in defined
    in_js = eid in referenced
    if in_html and in_js:
        print(f"  {GREEN}✓{RESET} {eid:<14} {DIM}{desc}{RESET}")
        ok += 1
    else:
        flag = []
        if not in_html:
            flag.append(f"{RED}HTML 里没有{RESET}")
        if not in_js:
            flag.append(f"{YELLOW}JS 没引用{RESET}")
        print(f"  {RED}✗{RESET} {eid:<14} {desc}  {' / '.join(flag)}")

print()
print(f"  {ok}/{len(METRO_IDS)} 个元素齐全")

# ══════════════════════════════════════════════════════════
#  5. 检查 CSS 类名是否和 JS 用的一致
# ══════════════════════════════════════════════════════════

print()
print(f"{BOLD}CSS 类名一致性{RESET}")
print()

# JS 里用到的类名（classList.add / toggle）
js_classes = set()
for m in re.finditer(r"""classList\.(?:add|remove|toggle)\(\s*['"]([\w-]+)['"]""", all_js):
    js_classes.add(m.group(1))

# CSS 里定义的类
css_match = re.search(r"<style>(.*?)</style>", html, re.S)
css = css_match.group(1) if css_match else ""
css_classes = set(re.findall(r"\.([\w-]+)\s*[,{:.\s]", css))

# 只看节拍器相关的
metro_classes = {"app-tab", "active", "playing", "meter-item", "beat",
                 "accent", "on", "app-tabs", "page", "dense", "open"}

print("  JS 操作的类：")
for c in sorted(js_classes):
    if c in metro_classes:
        in_css = c in css_classes
        mark = f"{GREEN}✓{RESET}" if in_css else f"{RED}✗{RESET}"
        print(f"    {mark} .{c}")
        if not in_css:
            print(f"        {RED}CSS 里没有这个类{RESET}")

# ══════════════════════════════════════════════════════════
print()
print("═" * 70)
print(f"{GREEN}{BOLD}✅ 交叉检查通过{RESET}")
print()
