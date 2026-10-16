#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 BPM 键盘输入的逻辑。

重点：
  · 非数字字符要被过滤掉
  · 超出范围要 clamp
  · 空输入不能把速度变成 0
  · 前导零、超长输入要处理对
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

# 取 BPM 范围
m_min = re.search(r"const BPM_MIN\s*=\s*(\d+)", html)
m_max = re.search(r"const BPM_MAX\s*=\s*(\d+)", html)
bpm_min = int(m_min.group(1))
bpm_max = int(m_max.group(1))

print()
print(f"{BOLD}BPM 输入逻辑验证{RESET}")
print("═" * 62)
print(f"\n  范围：{bpm_min} – {bpm_max}")

JS = r"""
var out = [];
var MIN = __MIN__, MAX = __MAX__;

function check(label, got, want) {
  out.push({ label: label, got: String(got), want: String(want),
             ok: String(got) === String(want) });
}

// ── 复刻界面里的过滤 + 限幅 ──

// 输入时的实时过滤（只留数字，最多 3 位）
function filterInput(raw) {
  return String(raw).replace(/[^0-9]/g, '').slice(0, 3);
}

// 确认时的取值
function clampBpm(v) {
  return Math.max(MIN, Math.min(MAX, Math.round(v)));
}

function commit(raw) {
  var cleaned = filterInput(raw);
  if (!cleaned) return null;          // 空输入 → 不改变
  return clampBpm(parseInt(cleaned, 10));
}

// ── 输入过滤 ──
check('纯数字',        filterInput('120'),   '120');
check('带字母',        filterInput('1a2b0'), '120');
check('带空格',        filterInput(' 88 '),  '88');
check('带小数点',      filterInput('120.5'), '120');
check('负数号',        filterInput('-60'),   '60');
check('超 3 位截断',   filterInput('1234'),  '123');
check('4 位被截',      filterInput('8888'),  '888');
check('全非数字',      filterInput('abc'),   '');
check('空字符串',      filterInput(''),      '');

// ── 确认取值 ──
check('正常 120',      commit('120'), 120);
check('偏慢 60',       commit('60'),  60);
check('偏快 200',      commit('200'), 200);
check('下界 30',       commit('30'),  30);
check('上界 250',      commit('250'), 250);

// 超范围 → clamp
check('太小变下界',    commit('10'),  MIN);
check('太小变下界 2',  commit('1'),   MIN);
check('太大变上界',    commit('999'), MAX);
check('太大变上界 2',  commit('500'), MAX);

// 边界附近
check('下界-1',        commit(String(MIN - 1)), MIN);
check('下界本身',      commit(String(MIN)),     MIN);
check('下界+1',        commit(String(MIN + 1)), MIN + 1);
check('上界-1',        commit(String(MAX - 1)), MAX - 1);
check('上界本身',      commit(String(MAX)),     MAX);
check('上界+1',        commit(String(MAX + 1)), MAX);

// 特殊输入
check('前导零 088',    commit('088'),  88);
check('全零 000',      commit('000'),  MIN);   // 0 → clamp 到最小值
check('空输入',        commit(''),     null);
check('只有字母',      commit('abc'),  null);
check('带中文',        commit('88拍'),  88);
check('带中文（小值）', commit('12拍'),  MIN);   // 12 小于下界，会被 clamp

JSON.stringify(out);
""".replace("__MIN__", str(bpm_min)).replace("__MAX__", str(bpm_max))

tmp = "/tmp/bpm_input_test.js"
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
        print(f"  {GREEN}✓{RESET} {r_['label']:<18} → {r_['got']}")
    else:
        fails += 1
        print(f"  {RED}✗{RESET} {r_['label']:<18} 得到 {r_['got']}  期望 {r_['want']}")

print()
print("═" * 62)
if fails:
    print(f"{RED}{BOLD}✗ {fails} 项失败（共 {len(results)} 项）{RESET}")
    sys.exit(1)
else:
    print(f"{GREEN}{BOLD}✅ {len(results)} 项全部通过{RESET}")
print()
