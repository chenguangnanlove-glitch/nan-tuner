#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""算出当前数字与圆环的比例，作为调整依据。"""

import os
import re

BASE = "/Users/nan/Desktop/始信调音器App"
html = open(os.path.join(BASE, "web", "index.html"), encoding="utf-8").read()

GREEN = "\033[32m"; YELLOW = "\033[33m"; DIM = "\033[2m"
BOLD = "\033[1m"; RESET = "\033[0m"


def blk(sel):
    m = re.search(re.escape(sel) + r"\{([^}]*)\}", html)
    return m.group(1) if m else ""


def num(block, prop, d=0):
    m = re.search(rf"{prop}:\s*(\d+(?:\.\d+)?)px", block)
    return float(m.group(1)) if m else d


print()
print(f"{BOLD}数字 vs 圆环比例{RESET}")
print("═" * 58)
print()

rows = []

# 基准
ring = num(blk(".metro-ring"), "max-height", 310)
bpm = num(blk(".ring-bpm"), "font-size", 64)
rows.append(("大屏", ring, bpm))

# 断点
for m in re.finditer(r"@media \(max-height:\s*(\d+)px\)\s*\{(.*?)\n  \}",
                     html, re.S):
    limit = int(m.group(1))
    body = m.group(2)
    r = re.search(r"\.metro-ring\{\s*max-height:(\d+)", body)
    b = re.search(r"\.ring-bpm\{\s*font-size:(\d+)", body)
    if r and b:
        rows.append((f"≤{limit}px", float(r.group(1)), float(b.group(1))))

print(f"  {'场景':<12} {'圆环':>7} {'数字':>7} {'占比':>8}  评估")
print("  " + "─" * 54)

for name, ring, bpm in rows:
    ratio = bpm / ring * 100
    if ratio < 28:
        note = f"{YELLOW}偏小{RESET}"
    elif ratio > 38:
        note = f"{YELLOW}偏大{RESET}"
    else:
        note = f"{GREEN}合适{RESET}"
    print(f"  {name:<12} {int(ring):>7} {int(bpm):>7} {ratio:>7.1f}%  {note}")

print()
print(f"  {DIM}目标：33% 左右（用户要求「起码三分之一」）{RESET}")
print()

targets = {}
for name, ring, bpm in rows:
    targets[name] = round(ring / 3)

print(f"{BOLD}建议的字号{RESET}")
print()
for name, ring, bpm in rows:
    t = round(ring / 3)
    print(f"  {name:<12} 圆环 {int(ring)}px  →  数字 {t}px（当前 {int(bpm)}px）")
print()
