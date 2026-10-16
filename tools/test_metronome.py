#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
用 osascript 实际运行节拍器的核心逻辑，验证计算结果。

语法检查只能证明代码"能解析"，这个测试证明"算得对"。
"""

import json
import os
import re
import subprocess
import sys

BASE = "/Users/nan/Desktop/始信调音器App"
GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"

html = open(os.path.join(BASE, "web", "index.html"), encoding="utf-8").read()

# 提取第 2 个 script 块（节拍器）
blocks = []
for m in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S):
    blocks.append(m.group(1))

metro_js = blocks[-1]

print()
print(f"{BOLD}节拍器核心逻辑 · 实际运行验证{RESET}")
print("═" * 70)

# ══════════════════════════════════════════════════════════
#  构造测试代码：把节拍器的核心部分截出来运行
#
#  只需要 accentPattern / tempoTerm / clampBpm / stepDen / clampNum，
#  它们不依赖 DOM。Metronome 需要 window，先跳过。
# ══════════════════════════════════════════════════════════

# 找到"界面控制"部分之前的内容（也就是核心逻辑 + 引擎）
split_marker = "/* ─────────── 3. 界面控制 ─────────── */"
core_part = metro_js.split(split_marker)[0] if split_marker in metro_js else metro_js

# 引擎部分依赖 window，但只是定义函数不执行，可以留着。
# 真正要跑的只有核心逻辑里的纯函数。

TEST_JS = core_part + r"""

// ════════ 测试 ════════
var out = [];

function check(label, got, want) {
  out.push({ label: label, got: String(got), want: String(want),
             ok: String(got) === String(want) });
}

// ── 重拍规则 ──
function pat(num, den) {
  return accentPattern(num, den).join('');
}

check('4/4',  pat(4,4),  '2000');
check('3/4',  pat(3,4),  '200');
check('2/4',  pat(2,4),  '20');
check('6/8',  pat(6,8),  '200100');
check('9/8',  pat(9,8),  '200100100');
check('12/8', pat(12,8), '200100100100');
check('3/8',  pat(3,8),  '200');
check('5/4',  pat(5,4),  '20000');
check('7/8',  pat(7,8),  '2000000');
check('6/6',  pat(6,6),  '200100');
check('12/12',pat(12,12),'200100100100');
check('5/12', pat(5,12), '20000');
check('2/6',  pat(2,6),  '20');

// ── 速度术语 ──
check('tempo 40',  tempoTerm(40).it,  'Grave');
check('tempo 60',  tempoTerm(60).it,  'Largo');
check('tempo 76',  tempoTerm(76).it,  'Adagio');
check('tempo 108', tempoTerm(108).it, 'Andante');
check('tempo 120', tempoTerm(120).it, 'Moderato');
check('tempo 168', tempoTerm(168).it, 'Allegro');
check('tempo 200', tempoTerm(200).it, 'Presto');
check('tempo 250', tempoTerm(250).it, 'Prestissimo');
check('tempo 120 中文', tempoTerm(120).cn, '中板');

// ── 边界 ──
check('clampBpm 上界', clampBpm(999), 250);
check('clampBpm 下界', clampBpm(1), 30);
check('clampNum 上界', clampNum(99), 12);
check('clampNum 下界', clampNum(-5), 2);
check('stepDen 4→6',   stepDen(4, 1), 6);
check('stepDen 6→8',   stepDen(6, 1), 8);
check('stepDen 12→2',  stepDen(12, 1), 2);
check('stepDen 2→12',  stepDen(2, -1), 12);
check('stepDen 4→2',   stepDen(4, -1), 2);
check('stepDen 8→6',   stepDen(8, -1), 6);

// ── 拍间隔 ──
// 用 Metronome 原型上的 beatDuration，需要构造对象
var m = new Metronome();
m.bpm = 120;
m.den = 4;
check('120 BPM 4/4 拍间隔', m.beatDuration().toFixed(4), '0.5000');
m.den = 8;
check('120 BPM 6/8 拍间隔', m.beatDuration().toFixed(4), '0.2500');
m.den = 2;
check('120 BPM 2/2 拍间隔', m.beatDuration().toFixed(4), '1.0000');
m.den = 12;
check('120 BPM 12分 拍间隔', m.beatDuration().toFixed(4), '0.1667');
m.den = 6;
check('120 BPM 6分 拍间隔', m.beatDuration().toFixed(4), '0.3333');
m.bpm = 60;
m.den = 4;
check('60 BPM 4/4 拍间隔', m.beatDuration().toFixed(4), '1.0000');

// ── setMeter 联动 ──
var m2 = new Metronome();
m2.setMeter(6, 8);
check('setMeter 分子', m2.num, 6);
check('setMeter 分母', m2.den, 8);
check('setMeter 重拍', m2.pattern.join(''), '200100');
check('meterLabel', m2.meterLabel(), '6/8');

JSON.stringify(out);
"""

# 写临时文件
tmp = "/tmp/metro_logic_test.js"
with open(tmp, "w", encoding="utf-8") as f:
    f.write(TEST_JS)

# 运行
script = f"""
ObjC.import('Foundation');
var path = '{tmp}';
var s = $.NSString.stringWithContentsOfFileEncodingError(path, $.NSUTF8StringEncoding, null);
var code = s.js;
try {{
  var result = eval(code);
  result;
}} catch (e) {{
  'RUNTIME_ERR: ' + e.message + ' @ ' + (e.line || '?');
}}
"""

r = subprocess.run(
    ["osascript", "-l", "JavaScript", "-e", script],
    capture_output=True, text=True, timeout=60,
)

out = r.stdout.strip()
err = r.stderr.strip()

if out.startswith("RUNTIME_ERR") or not out:
    print(f"\n  {RED}✗ 运行出错{RESET}")
    print(f"    {out or err}")
    sys.exit(1)

# 解析结果
try:
    # osascript 返回的 JSON 可能被转义
    raw = out.replace("\\\"", '"')
    if raw.startswith('"') and raw.endswith('"'):
        raw = raw[1:-1]
    raw = raw.encode().decode("unicode_escape")
    results = json.loads(raw)
except Exception as e:
    print(f"\n  {YELLOW}!{RESET} 结果解析失败：{e}")
    print(f"    {DIM}{out[:300]}{RESET}")
    sys.exit(1)

# 显示
print()
fails = 0
for r_ in results:
    if r_["ok"]:
        print(f"  {GREEN}✓{RESET} {r_['label']:<22} {r_['got']}")
    else:
        fails += 1
        print(f"  {RED}✗{RESET} {r_['label']:<22} 得到 {r_['got']}  期望 {r_['want']}")

print()
print("═" * 70)
print()
if fails:
    print(f"{RED}{BOLD}✗ {fails} 项失败（共 {len(results)} 项）{RESET}")
    sys.exit(1)
else:
    print(f"{GREEN}{BOLD}✅ {len(results)} 项全部通过（实际运行 JS 验证）{RESET}")
print()
