#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把硬编码的主题色改成引用 CSS 变量（修正版）。

上一版有两个 bug：
  1. 兜底替换把 :root 里的定义也改了，产生 --accent:var(--accent) 自引用
  2. 先替换了通用 rgba，导致 JS 里那条完整语句再也匹配不上

这一版的顺序：
  1. 先把 :root 区块整个挖出来，用占位符代替
  2. 在剩余内容上做所有替换（不会碰到变量定义）
  3. 最后把新的 :root 放回去
"""

import os
import re
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, "web", "index.html")

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"

PLACEHOLDER = "/*__ROOT_BLOCK_PLACEHOLDER__*/"


def hex_to_rgb(h):
    h = h.lstrip("#")
    if len(h) == 3:
        h = "".join(c * 2 for c in h)
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def lighten(hexcolor, amount=0.28):
    r, g, b = hex_to_rgb(hexcolor)
    r = int(r + (255 - r) * amount)
    g = int(g + (255 - g) * amount)
    b = int(b + (255 - b) * amount)
    return f"#{r:02x}{g:02x}{b:02x}"


text = open(WEB, encoding="utf-8").read()

# ── 幂等检查：已经改造过就不再改 ──
if "--accent-rgb" in text and "function theme()" in text:
    print()
    print(f"{GREEN}✓ 已经是改造后的版本，无需重复运行{RESET}")
    print()
    print(f"  {DIM}（这个脚本只在从旧版本升级时需要用一次）{RESET}")
    print()
    sys.exit(0)

# ══════════════════════════════════════════════════════════
#  读当前配色
# ══════════════════════════════════════════════════════════

m = re.search(r":root\{(.*?)\}", text, re.S)
if not m:
    sys.exit(f"{RED}找不到 :root 区块{RESET}")

block = m.group(1)


def grab(var, default=None):
    mm = re.search(rf"{re.escape(var)}\s*:\s*([^;]+);", block)
    return mm.group(1).strip() if mm else default


cur = {
    "bg": grab("--bg", "#0e0c0a"),
    "surface": grab("--surface", "#1a1815"),
    "surface2": grab("--surface-2", "#211f1b"),
    "surface3": grab("--surface-3", "#2b2823"),
    "text": grab("--text", "#f0ebe3"),
    "text2": grab("--text-2", "#948a7d"),
    "text3": grab("--text-3", "#5e5750"),
    "accent": grab("--accent", "#d4a574"),
    "success": grab("--success", "#8fbf7a"),
    "warn": grab("--warn", "#e0a458"),
}

accent = cur["accent"]
success = cur["success"]
warn = cur["warn"]

accent_rgb = ",".join(str(x) for x in hex_to_rgb(accent))
success_rgb = ",".join(str(x) for x in hex_to_rgb(success))
warn_rgb = ",".join(str(x) for x in hex_to_rgb(warn))
accent_light = lighten(accent, 0.28)
accent_light_rgb = ",".join(str(x) for x in hex_to_rgb(accent_light))

accent_rgb_old = ",".join(str(x) for x in hex_to_rgb("#d4a574"))
success_rgb_old = ",".join(str(x) for x in hex_to_rgb("#8fbf7a"))

print()
print(f"{BOLD}当前配色{RESET}")
print("─" * 66)
print(f"  主色      {accent}")
print(f"  成功色    {success}")
print(f"  警示色    {warn}")
print()
print(f"  推导：")
print(f"    浅色版    {accent_light}")
print(f"    主色 RGB  {accent_rgb}")

# ══════════════════════════════════════════════════════════
#  第一步：把 :root 挖出来，避免被后续替换污染
# ══════════════════════════════════════════════════════════

text = text[:m.start()] + PLACEHOLDER + text[m.end():]

changes = []


def sub(pattern, replacement, desc, expect=1):
    global text
    new, n = re.subn(pattern, replacement, text)
    if n:
        text = new
        changes.append((desc, n))
    elif expect:
        changes.append((f"{RED}未匹配：{desc}{RESET}", 0))
    return n


# ══════════════════════════════════════════════════════════
#  第二步：处理 JS 里的特殊语句（必须在通用替换之前）
# ══════════════════════════════════════════════════════════

# 频闪条纹色（整条语句）
sub(
    r"strobeCtx\.fillStyle\s*=\s*inTune\s*\?\s*'rgba\(143\s*,\s*191\s*,\s*122\s*,\s*\.55\)'\s*:\s*'rgba\(212\s*,\s*165\s*,\s*116\s*,\s*\.42\)'\s*;",
    "strobeCtx.fillStyle = inTune\n"
    "        ? `rgba(${theme().successRgb},.55)`\n"
    "        : `rgba(${theme().accentRgb},.42)`;",
    "频闪条纹色（JS）",
)

# 频闪背景色
sub(
    r"strobeCtx\.fillStyle\s*=\s*'#211f1b'\s*;",
    "strobeCtx.fillStyle = theme().surface2;",
    "频闪背景色（JS）",
)

# ══════════════════════════════════════════════════════════
#  第三步：通用替换（此时 :root 已被挖走，安全）
# ══════════════════════════════════════════════════════════

# 旧的金色/绿色 rgba（写死的原始值）
sub(rf"rgba\(\s*{accent_rgb_old}\s*,", "rgba(var(--accent-rgb),",
    "金色 rgba")
sub(rf"rgba\(\s*{success_rgb_old}\s*,", "rgba(var(--success-rgb),",
    "绿色 rgba")

# 主按钮渐变
sub(r"linear-gradient\(180deg\s*,\s*#e8c197\s*,\s*#d4a574\s*\)",
    "linear-gradient(180deg, var(--accent-light), var(--accent))",
    "主按钮渐变")

# SVG：presentation attribute（stop-color="..."）不支持 var()，
# 必须换成 style 属性。必须在通用 hex 替换之前做。
sub(r'stop-color="#e8c197"', 'style="stop-color:var(--accent-light)"',
    "SVG 渐变起始色（改 style 属性）")
sub(r'stop-color="#d4a574"', 'style="stop-color:var(--accent)"',
    "SVG 渐变结束色（改 style 属性）")
sub(r'fill="#d4a574"', 'style="fill:var(--accent)"',
    "SVG 指针圆点（改 style 属性）")

# 十六进制（剩下的）
sub(r"#e8c197", "var(--accent-light)", "浅金 hex")
sub(r"#d4a574", "var(--accent)", "金色 hex")

# ══════════════════════════════════════════════════════════
#  第四步：写回新的 :root
# ══════════════════════════════════════════════════════════

new_root = f""":root{{
    --bg:{cur['bg']};
    --surface:{cur['surface']};
    --surface-2:{cur['surface2']};
    --surface-3:{cur['surface3']};
    --border:rgba(240,235,227,.06);
    --border-2:rgba(240,235,227,.10);
    --text:{cur['text']};
    --text-2:{cur['text2']};
    --text-3:{cur['text3']};

    /* 主题色
       改配色时，下面这 6 个要一起改（见 tools/ui_tool.py） */
    --accent:{accent};
    --accent-light:{accent_light};
    --accent-soft:rgba({accent_rgb},.13);
    --accent-rgb:{accent_rgb};
    --accent-light-rgb:{accent_light_rgb};

    --success:{success};
    --success-rgb:{success_rgb};
    --warn:{warn};
    --warn-rgb:{warn_rgb};
  }}"""

text = text.replace(PLACEHOLDER, new_root)

# ══════════════════════════════════════════════════════════
#  第五步：插入 theme() 辅助函数
# ══════════════════════════════════════════════════════════

THEME_HELPER = """
  /* ===== 读取主题色（由 tools/fix_theme.py 自动插入）=====
     画布（canvas）读不到 CSS 变量，只能在运行时取出来。
     只读一次就缓存 —— getComputedStyle 很慢，不能放在动画循环里。 */
  let __themeCache = null;
  function theme(){
    if (__themeCache) return __themeCache;
    let cs = null;
    try { cs = getComputedStyle(document.documentElement); } catch(e){}
    const get = (name, fallback) => {
      if (!cs) return fallback;
      const v = cs.getPropertyValue(name);
      return (v && v.trim()) || fallback;
    };
    __themeCache = {
      accent:     get('--accent', '#d4a574'),
      accentRgb:  get('--accent-rgb', '212,165,116'),
      successRgb: get('--success-rgb', '143,191,122'),
      surface2:   get('--surface-2', '#211f1b'),
      text:       get('--text', '#f0ebe3')
    };
    return __themeCache;
  }

"""

mm = re.search(r"<script>\s*\n", text)
if mm and "function theme()" not in text:
    text = text[:mm.end()] + THEME_HELPER + text[mm.end():]
    changes.append(("插入 theme() 辅助函数", 1))

# ══════════════════════════════════════════════════════════
#  写入
# ══════════════════════════════════════════════════════════

shutil.copy2(WEB, WEB + ".pre-theme.bak")
with open(WEB, "w", encoding="utf-8") as f:
    f.write(text)

print()
print(f"{BOLD}改动清单{RESET}")
print("─" * 66)
bad = 0
for desc, n in changes:
    if n == 0:
        print(f"  {RED}✗{RESET} {desc}")
        bad += 1
    else:
        print(f"  {GREEN}✓{RESET} {desc}（{n} 处）")

print()
if bad:
    print(f"  {RED}有 {bad} 项没匹配上，需要检查{RESET}")
else:
    print(f"  {GREEN}全部完成{RESET}")

print()
print(f"  {DIM}备份：web/index.html.pre-theme.bak{RESET}")
print()
