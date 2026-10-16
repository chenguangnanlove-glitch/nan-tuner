#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证圆环拖动调速的数学逻辑。

关键风险点在「角度跨越 ±180° 边界」：
手指从 170° 转到 -170°，实际只转了 20°，
但直接相减会得到 -340°，导致 BPM 突然暴跌。
"""

import json
import os
import subprocess
import sys

BASE = "/Users/nan/Desktop/始信调音器App"
GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"

html = open(os.path.join(BASE, "web", "index.html"), encoding="utf-8").read()

# 取 DRAG_BPM_PER_TURN 的值
import re
m = re.search(r"DRAG_BPM_PER_TURN\s*=\s*(\d+)", html)
per_turn = int(m.group(1)) if m else 90

print()
print(f"{BOLD}圆环拖动逻辑验证{RESET}")
print("═" * 66)
print(f"\n  每转一圈变化：{per_turn} BPM")

# ══════════════════════════════════════════════════════════
#  复刻前端的角度增量算法
# ══════════════════════════════════════════════════════════

JS = r"""
var out = [];
var PER_TURN = __PER_TURN__;

// 复刻界面里的角度增量处理
function stepDelta(prev, cur) {
  var d = cur - prev;
  if (d > 180) d -= 360;
  if (d < -180) d += 360;
  return d;
}

function check(label, got, want) {
  var ok = (Math.abs(got - want) < 1e-6);
  out.push({ label: label, got: got.toFixed(2), want: want.toFixed(2), ok: ok });
}

// ── 角度增量 ──
check('普通增量 +30',      stepDelta(10, 40),     30);
check('普通增量 -30',      stepDelta(40, 10),    -30);
check('跨 180° 正向',      stepDelta(170, -170),  20);
check('跨 180° 反向',      stepDelta(-170, 170), -20);
check('跨 0° 正向',        stepDelta(-10, 10),    20);
check('跨 0° 反向',        stepDelta(10, -10),   -20);
check('转一整圈',          stepDelta(0, 0),        0);

// ── BPM 映射 ──
function bpmDelta(accumDeg) {
  return Math.round(accumDeg / 360 * PER_TURN);
}

check('转 90° 变化',   bpmDelta(90),  Math.round(90/360*PER_TURN));
check('转 180° 变化',  bpmDelta(180), Math.round(180/360*PER_TURN));
check('转一圈变化',    bpmDelta(360), PER_TURN);
check('转两圈变化',    bpmDelta(720), PER_TURN * 2);
check('反向转一圈',    bpmDelta(-360), -PER_TURN);
check('只转 4° ',      bpmDelta(4),   Math.round(4/360*PER_TURN));
check('转 1° ',        bpmDelta(1),   Math.round(1/360*PER_TURN));

// ── 模拟真实拖动：从 120 BPM 开始转 3 次，每次 40° ──
var accum = 0, start = 120, angles = [0, 40, 80, 120];
var prev = angles[0];
var trace = [];
for (var i = 1; i < angles.length; i++) {
  accum += stepDelta(prev, angles[i]);
  prev = angles[i];
  trace.push(Math.round(start + accum / 360 * PER_TURN));
}
out.push({ label: '连续拖动 120°', got: trace.join(','), want: '130,140,150',
           ok: trace.length === 3 && trace[0] === 130 && trace[1] === 140 && trace[2] === 150 });

// ── 模拟跨越边界：从 170° 连续转到 -170° ──
accum = 0;
var seq = [170, 180, -170];
prev = seq[0];
var tr2 = [];
for (var k = 1; k < seq.length; k++) {
  accum += stepDelta(prev, seq[k]);
  prev = seq[k];
}
out.push({ label: '跨边界累计应为 20°', got: accum.toFixed(1), want: '20.0',
           ok: Math.abs(accum - 20) < 1e-6 });

JSON.stringify(out);
""".replace("__PER_TURN__", str(per_turn))

tmp = "/tmp/drag_test.js"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(JS)

script = f"""
ObjC.import('Foundation');
var s = $.NSString.stringWithContentsOfFileEncodingError('{tmp}', $.NSUTF8StringEncoding, null);
try {{ eval(s.js); }} catch (e) {{ 'RUNTIME_ERR: ' + e.message; }}
"""

r = subprocess.run(["osascript", "-l", "JavaScript", "-e", script],
                   capture_output=True, text=True, timeout=30)
out = r.stdout.strip()

if not out or out.startswith("RUNTIME_ERR"):
    print(f"\n  {RED}✗ 运行失败：{out or r.stderr}{RESET}\n")
    sys.exit(1)

raw = out
if raw.startswith('"') and raw.endswith('"'):
    raw = raw[1:-1]
raw = raw.replace('\\"', '"').encode().decode("unicode_escape")
results = json.loads(raw)

print()
fails = 0
for r_ in results:
    if r_["ok"]:
        print(f"  {GREEN}✓{RESET} {r_['label']:<22} {r_['got']}")
    else:
        fails += 1
        print(f"  {RED}✗{RESET} {r_['label']:<22} 得到 {r_['got']}  期望 {r_['want']}")

print()
print("═" * 66)
print()
if fails:
    print(f"{RED}{BOLD}✗ {fails} 项失败（共 {len(results)} 项）{RESET}")
    sys.exit(1)
else:
    print(f"{GREEN}{BOLD}✅ {len(results)} 项全部通过{RESET}")
    print()
    print(f"  {DIM}手感估算：转 4° 变化 1 BPM，转一圈变化 {per_turn} BPM{RESET}")
print()
