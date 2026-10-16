#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
布局适配检查。

按屏幕高度分档，确认：
  · 圆环不被撑出屏幕
  · 圆环内的内容（数字 + 术语）不碰到圆环
  · 数字与圆环的比例接近 1/3
"""

import os
import re
import sys

BASE = "/Users/nan/Desktop/始信调音器App"
GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"

html = open(os.path.join(BASE, "web", "index.html"), encoding="utf-8").read()


def blk(sel):
    m = re.search(re.escape(sel) + r"\{([^}]*)\}", html)
    return m.group(1) if m else ""


def px(block, prop, default=0):
    m = re.search(rf"{prop}:\s*(\d+(?:\.\d+)?)px", block)
    return float(m.group(1)) if m else default


# ── 基准值 ──
BASE_SIZES = {
    "ring":     px(blk(".metro-ring"), "max-height", 310),
    "bpm":      px(blk(".ring-bpm"), "font-size", 100),
    "term":     px(blk(".ring-term"), "font-size", 13),
    "term_mt":  px(blk(".ring-term"), "margin-top", 8),
    "center_w": 80.0,
}

# ── 断点 ──
BREAKPOINTS = []
for m in re.finditer(r"@media \(max-height:\s*(\d+)px\)\s*\{(.*?)\n  \}", html, re.S):
    limit = int(m.group(1))
    body = m.group(2)
    over = {}

    r = re.search(r"\.metro-ring\{\s*max-height:(\d+(?:\.\d+)?)px", body)
    if r:
        over["ring"] = float(r.group(1))
    b = re.search(r"\.ring-bpm\{\s*font-size:(\d+(?:\.\d+)?)px", body)
    if b:
        over["bpm"] = float(b.group(1))
    t = re.search(r"\.ring-term\{\s*font-size:(\d+(?:\.\d+)?)px", body)
    if t:
        over["term"] = float(t.group(1))
    tm = re.search(r"\.ring-term\{[^}]*margin-top:(\d+(?:\.\d+)?)px", body)
    if tm:
        over["term_mt"] = float(tm.group(1))
    c = re.search(r"\.ring-center\{\s*width:(\d+(?:\.\d+)?)%", body)
    if c:
        over["center_w"] = float(c.group(1))

    if over:
        BREAKPOINTS.append((limit, over))

BREAKPOINTS.sort(key=lambda x: -x[0])

# 固定开销
FIXED = 178


def sizes_for(h):
    s = dict(BASE_SIZES)
    for limit, over in BREAKPOINTS:
        if h <= limit:
            s.update(over)
    return s


print()
print(f"{BOLD}布局适配检查{RESET}")
print("═" * 70)
print()
print(f"  {BOLD}基准（大屏）{RESET}")
print(f"    圆环      {int(BASE_SIZES['ring'])}px")
print(f"    数字      {int(BASE_SIZES['bpm'])}px  ({BASE_SIZES['bpm']/BASE_SIZES['ring']*100:.1f}%)")
print(f"    术语      {int(BASE_SIZES['term'])}px")
print()
print(f"  {BOLD}断点{RESET}")
for limit, over in BREAKPOINTS:
    s = "  ".join(f"{k}={int(v)}" for k, v in over.items())
    print(f"    屏高 ≤{limit}px : {s}")

# ══════════════════════════════════════════════════════════
print()
print(f"{BOLD}各机型{RESET}")
print()
print(f"  {'机型':<18} {'屏高':>5} {'圆环':>5} {'数字':>5} {'比例':>6} {'内容':>5} {'可用':>5}  结果")
print("  " + "─" * 70)

DEVICES = [
    ("iPhone 14 Pro Max", 932),
    ("iPhone 14", 844),
    ("iPhone 12 mini", 812),
    ("安卓中屏", 780),
    ("iPhone SE", 667),
    ("安卓小屏", 640),
    ("横屏", 430),
    ("极矮屏", 390),
    ("很极端", 340),
]

problems = []

for name, h in DEVICES:
    s = sizes_for(h)
    avail = h - FIXED
    ring = min(s["ring"], max(100, avail))

    # 内容高：数字行高约 0.92，加 padding 上下 6px；术语 1.4 倍行高 + margin
    num_h = s["bpm"] * 0.92 + 12
    term_h = s["term"] * 1.4 + s["term_mt"]
    content = num_h + term_h

    # 圆环内可用直径：SVG 圆 r=90/200 → 90% 直径
    inner = ring * 0.90
    # 内容宽度按 center_w 限制
    usable = inner * (s["center_w"] / 100)

    ratio = s["bpm"] / ring * 100

    ok_h = content <= inner * 0.95
    ok_fit = (FIXED + ring) <= h

    if ok_h and ok_fit:
        status = f"{GREEN}✓{RESET}"
    else:
        status = f"{RED}✗{RESET}"
        if not ok_h:
            problems.append(f"{name}: 内容 {int(content)}px > 内径 {int(inner * 0.95)}px")
        if not ok_fit:
            problems.append(f"{name}: 整体溢出")

    print(f"  {name:<18} {h:>5} {int(ring):>5} {int(s['bpm']):>5} "
          f"{ratio:>5.0f}% {int(content):>5} {int(inner * 0.95):>5}  {status}")

# ══════════════════════════════════════════════════════════
print()
print(f"{BOLD}比例检查（用户要求 ≥ 1/3）{RESET}")
print()

for name, h in DEVICES[:6]:
    s = sizes_for(h)
    avail = h - FIXED
    ring = min(s["ring"], max(100, avail))
    ratio = s["bpm"] / ring * 100
    mark = f"{GREEN}✓{RESET}" if ratio >= 30 else f"{YELLOW}~{RESET}"
    print(f"  {mark} {name:<18} {ratio:.0f}%")
    if ratio < 30:
        problems.append(f"{name} 比例偏低（{ratio:.0f}%）")

print()
print("═" * 70)
print()
if problems:
    print(f"{RED}{BOLD}✗ {len(problems)} 个问题：{RESET}")
    for p in problems:
        print(f"    · {p}")
    sys.exit(1)
else:
    print(f"{GREEN}{BOLD}✅ 所有尺寸都正常{RESET}")
    print()
    print(f"  {DIM}数字与圆环的比例保持在 1/3 左右。{RESET}")
print()
