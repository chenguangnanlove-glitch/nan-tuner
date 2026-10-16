#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证节拍器整合后的 HTML 结构。

重点：
  1. 标签配对
  2. 调音器原有内容一行没丢
  3. 新增的节拍器元素都在
"""

import html.parser
import os
import re
import sys

BASE = "/Users/nan/Desktop/始信调音器App"
WEB = os.path.join(BASE, "web", "index.html")
BEFORE = "/tmp/before_metro.html"

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"

VOID = {"area", "base", "br", "col", "embed", "hr", "img", "input",
        "link", "meta", "param", "source", "track", "wbr"}


class Checker(html.parser.HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.stack = []
        self.bad = []
        self.ids = []

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)
        if d.get("id"):
            self.ids.append(d["id"])
        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        d = dict(attrs)
        if d.get("id"):
            self.ids.append(d["id"])

    def handle_endtag(self, tag):
        if tag in VOID:
            return
        if not self.stack:
            self.bad.append(f"第 {self.getpos()[0]} 行：多余的 </{tag}>")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    unclosed = [t for t, _ in self.stack[i + 1:]]
                    self.bad.append(
                        f"第 {self.getpos()[0]} 行 </{tag}> 之前有未闭合：{unclosed}")
                    self.stack = self.stack[:i]
                    return
            self.bad.append(f"第 {self.getpos()[0]} 行：</{tag}> 没有开始标签")


print()
print(f"{BOLD}整合结果验证{RESET}")
print("═" * 68)

text = open(WEB, encoding="utf-8").read()
before = open(BEFORE, encoding="utf-8").read()

problems = []

# ══════════════════════════════════════════════════════════
print()
print(f"{BOLD}1. 标签配对{RESET}")
print()

c = Checker()
c.feed(text)
c.close()

if c.bad:
    for b in c.bad[:5]:
        problems.append(b)
        print(f"  {RED}✗{RESET} {b}")
else:
    print(f"  {GREEN}✓{RESET} 标签全部配对")

if c.stack:
    leftovers = [f"{t}(第{l}行)" for t, l in c.stack]
    problems.append(f"未闭合：{leftovers}")
    print(f"  {RED}✗ 未闭合：{leftovers}{RESET}")
else:
    print(f"  {GREEN}✓{RESET} 没有未闭合标签")

# 重复 id
dupes = [i for i in set(c.ids) if c.ids.count(i) > 1]
if dupes:
    problems.append(f"重复 id：{dupes}")
    print(f"  {RED}✗ 重复 id：{dupes}{RESET}")
else:
    print(f"  {GREEN}✓{RESET} {len(c.ids)} 个 id 均唯一")

# ══════════════════════════════════════════════════════════
print()
print(f"{BOLD}2. 调音器原有内容是否完整{RESET}")
print()

before_lines = [l for l in before.splitlines() if l.strip()]
lost = [l for l in before_lines if l not in text]

if lost:
    problems.append(f"丢失 {len(lost)} 行")
    print(f"  {RED}✗ 丢失 {len(lost)} 行：{RESET}")
    for l in lost[:5]:
        print(f"      {l.strip()[:70]}")
else:
    print(f"  {GREEN}✓{RESET} 原有 {len(before_lines)} 行全部保留")

# 核心功能
core = {
    "音高检测": "detectPitch",
    "麦克风": "getUserMedia",
    "频闪": "strobeCanvas",
    "钢琴键": "buildPianoKeys",
    "指针": "needleDot",
    "主题色函数": "function theme()",
}
all_core = True
for name, marker in core.items():
    if marker not in text:
        problems.append(f"缺 {name}")
        all_core = False
for name, marker in core.items():
    mark = f"{GREEN}✓{RESET}" if marker in text else f"{RED}✗{RESET}"
    print(f"  {mark} {name}")

# ══════════════════════════════════════════════════════════
print()
print(f"{BOLD}3. 节拍器元素{RESET}")
print()

metro_ids = ["appTabs", "tabTuner", "tabMetro", "pageMetro",
             "meterBtn", "meterLabel", "meterSheet", "meterClose",
             "numGrid", "denGrid",
             "metroRing", "ringProgress", "pulseRing",
             "bpmValue", "bpmInput", "bpmTerm", "ringCenter",
             "beatDots"]

missing = []
for mid in metro_ids:
    if f'id="{mid}"' not in text:
        missing.append(mid)

if missing:
    problems.append(f"缺元素：{missing}")
    print(f"  {RED}✗ 缺少：{missing}{RESET}")
else:
    print(f"  {GREEN}✓{RESET} {len(metro_ids)} 个节拍器元素齐全")

# pageTuner
if 'id="pageTuner"' in text:
    print(f"  {GREEN}✓{RESET} 调音页容器 pageTuner")
else:
    problems.append("缺 pageTuner")
    print(f"  {RED}✗ 缺 pageTuner{RESET}")

# ══════════════════════════════════════════════════════════
print()
print(f"{BOLD}4. 页面结构{RESET}")
print()

# 检查 pageTuner 是否在 pageMetro 之前
i_tuner = text.find('id="pageTuner"')
i_metro = text.find('id="pageMetro"')
if i_tuner > 0 and i_metro > 0:
    if i_tuner < i_metro:
        print(f"  {GREEN}✓{RESET} 调音页在前，节拍页在后")
    else:
        problems.append("页面顺序反了")
        print(f"  {RED}✗ 页面顺序反了{RESET}")

# 检查嵌套：pageMetro 应该在 .app 里面
app_close = text.rfind("\n</div>", 0, text.find("<script>"))
if i_metro < app_close:
    print(f"  {GREEN}✓{RESET} 节拍页在 .app 容器内")
else:
    problems.append("节拍页跑到 .app 外面了")
    print(f"  {RED}✗ 节拍页在 .app 外面{RED}")

# ── 显示插入位置附近的结构 ──
print()
print(f"  {DIM}插入位置附近：{RESET}")
lines = text.splitlines()
for i, l in enumerate(lines):
    if 'id="pageMetro"' in l:
        for j in range(max(0, i - 4), min(len(lines), i + 2)):
            marker = "→" if j == i else " "
            print(f"  {marker} {lines[j][:76]}")
        break

# ══════════════════════════════════════════════════════════
print()
print(f"{BOLD}5. 样式{RESET}")
print()

css_checks = [
    (".app-tabs", "切换键容器"),
    (".app-tab.active", "切换键选中态"),
    (".app-tabs-thumb", "滑块"),
    (".meter-btn", "拍号按钮"),
    (".meter-item", "拍号选项"),
    (".meter-sheet", "拍号面板"),
    (".ring-progress", "进度弧"),
    (".pulse-ring", "脉冲环"),
    (".ring-bpm", "BPM 数字"),
    (".ring-bpm-input", "BPM 输入框"),
    (".ring-bpm.playing", "播放中数字变色"),
    (".beat-dot", "拍点"),
    ("@keyframes metroPulse", "脉冲动画"),
]
for cls, desc in css_checks:
    mark = f"{GREEN}✓{RESET}" if cls in text else f"{RED}✗{RESET}"
    if cls not in text:
        problems.append(f"缺样式 {cls}")
    print(f"  {mark} {desc}")

# ══════════════════════════════════════════════════════════
print()
print("═" * 68)
if problems:
    print(f"{RED}{BOLD}✗ {len(problems)} 个问题{RESET}")
    for p in problems[:8]:
        print(f"    · {p}")
    sys.exit(1)
else:
    print(f"{GREEN}{BOLD}✅ 结构完整，可以插入 JS{RESET}")
print()
