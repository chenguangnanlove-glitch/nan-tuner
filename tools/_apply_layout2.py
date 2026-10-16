#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
调音页第二批布局调整（垂直节奏对齐）。

目标（页面坐标，390×780）：
  乐器按钮 116-158 / 表盘弧圆心 390 / 弦按钮 524-580 /
  音量条 624-632 / 开始调音 672-720

本脚本只做精确字符串替换，逐条校验命中数。
"""

import io
import sys

P = "web/index.html"
s = io.open(P, encoding="utf-8").read()
before = len(s)

REPS = [
    # 钢琴八度行：高度锁 32（482-514），btn 相应缩小
    ("    gap:16px;margin-bottom:14px;\n  }\n  .oct-btn{\n    width:40px;height:36px;border-radius:10px;",
     "    gap:14px;margin-bottom:10px;height:32px;\n  }\n  .oct-btn{\n    width:36px;height:32px;border-radius:9px;"),

    # 八度显示框
    ("    min-width:78px;text-align:center;\n    font-size:14px;font-weight:500;color:var(--text);\n"
     "    letter-spacing:.08em;font-variant-numeric:tabular-nums;\n    padding:7px 14px;border-radius:9px;",
     "    min-width:74px;text-align:center;\n    font-size:13px;font-weight:500;color:var(--text);\n"
     "    letter-spacing:.08em;font-variant-numeric:tabular-nums;\n    padding:6px 12px;border-radius:9px;"),

    # 琴键：高度锁 56，与弦按钮同高
    ("  .piano-keys{display:grid;grid-template-columns:repeat(6,1fr);gap:6px}",
     "  .piano-keys{\n    display:grid;grid-template-columns:repeat(6,1fr);\n"
     "    grid-template-rows:repeat(2,1fr);\n    gap:6px;height:56px;\n  }"),

    # 琴键按钮：去掉大 padding，靠 grid 分配高度
    ("    font-size:12px;font-weight:500;\n    padding:14px 2px;border-radius:10px;",
     "    font-size:11.5px;font-weight:500;\n    padding:0 2px;border-radius:9px;"),

    # 主按钮：上移定位，高度压到 48
    ("    font-family:inherit;\n    padding:18px;border-radius:14px;\n    font-size:15px;font-weight:500;",
     "    font-family:inherit;\n    margin-top:40px;\n    padding:15px;border-radius:14px;\n"
     "    font-size:15px;font-weight:500;"),

    # 提示行：收紧
    ("    color:var(--text-3);\n    margin-top:14px;\n    letter-spacing:.04em;",
     "    color:var(--text-3);\n    margin-top:8px;\n    letter-spacing:.04em;"),
]

fails = []
for i, (a, b) in enumerate(REPS):
    n = s.count(a)
    if n == 1:
        s = s.replace(a, b)
        print(f"  [{i}] ok")
    else:
        print(f"  [{i}] 命中 {n} 次 —— 跳过")
        fails.append(i)

io.open(P, "w", encoding="utf-8").write(s)
print(f"\n字符数 {before} -> {len(s)}")
if fails:
    sys.exit(f"有 {len(fails)} 条没命中：{fails}")
print("全部替换完成")
