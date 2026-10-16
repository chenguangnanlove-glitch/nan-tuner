#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成配色对比图，直观展示换主色调的效果。

模拟调音器界面的关键元素（背景 + 卡片 + 指针 + 音符），
每种配色方案画一份，拼成一张对照图。
"""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    sys.exit("需要 Pillow")

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "tools", "配色对比.png")

# ── 配色方案：(名称, 背景, 卡片, 主色, 主色RGB用于半透明, 文字) ──
SCHEMES = [
    ("现在的（金）",  "#0e0c0a", "#1a1815", "#d4a574", (212, 165, 116), "#f0ebe3"),
    ("天蓝",          "#0a0f1a", "#141a26", "#4a90d9", (74, 144, 217),  "#eef3fa"),
    ("薄荷绿",        "#0a1210", "#131f1c", "#4fb8a5", (79, 184, 165),  "#eaf5f2"),
    ("珊瑚橙",        "#120c0a", "#1f1614", "#e07a5f", (224, 122, 95),  "#f7ece8"),
    ("紫罗兰",        "#0e0a14", "#181323", "#9d7cd8", (157, 124, 216), "#f1ecfa"),
    ("玫红",          "#120a0e", "#1f1319", "#d96a8a", (217, 106, 138), "#faeef2"),
]

# ── 画布尺寸 ──
CARD_W, CARD_H = 240, 300
GAP = 26
COLS = 3
ROWS = (len(SCHEMES) + COLS - 1) // COLS
PAD = 30
TITLE_H = 26

W = PAD * 2 + CARD_W * COLS + GAP * (COLS - 1)
H = PAD * 2 + (CARD_H + TITLE_H) * ROWS + GAP * (ROWS - 1)

SS = 3   # 超采样，先画大图再缩小，边缘更平滑
img = Image.new("RGB", (W * SS, H * SS), (26, 24, 22))
d = ImageDraw.Draw(img)


def load_font(size):
    """找一个能显示中文的字体。"""
    candidates = [
        "/System/Library/Fonts/PingFang.ttc",
        "/System/Library/Fonts/STHeiti Light.ttc",
        "/System/Library/Fonts/Hiragino Sans GB.ttc",
        "/Library/Fonts/Arial Unicode.ttf",
    ]
    for c in candidates:
        if os.path.isfile(c):
            try:
                return ImageFont.truetype(c, size)
            except Exception:
                continue
    return ImageFont.load_default()


F_TITLE = load_font(17 * SS)
F_NOTE = load_font(46 * SS)
F_SMALL = load_font(11 * SS)
F_CENTS = load_font(13 * SS)


def hex2rgb(h):
    h = h.lstrip("#")
    return tuple(int(h[i:i + 2], 16) for i in (0, 2, 4))


def draw_scheme(x, y, name, bg, card, accent, accent_rgb, text):
    """画一张模拟的调音器界面。

    注意：传入的 x, y 已经是超采样坐标，
    所以下面所有逻辑尺寸（CARD_W 等）都要乘 SS。
    """
    bg_c = hex2rgb(bg)
    card_c = hex2rgb(card)
    accent_c = hex2rgb(accent)
    text_c = hex2rgb(text)

    card_w = CARD_W * SS
    card_h = CARD_H * SS

    # 标题
    d.text((x, y), name, font=F_TITLE, fill=(200, 195, 188))

    y0 = y + TITLE_H * SS

    # 卡片（圆角）
    d.rounded_rectangle(
        [x, y0, x + card_w, y0 + card_h],
        radius=20 * SS, fill=card_c,
        outline=tuple(min(255, c + 20) for c in card_c), width=SS,
    )

    cx = x + card_w // 2          # 卡片水平中心
    pad = 22 * SS

    # ── 顶部：品牌名 ──
    d.text((x + pad, y0 + 24 * SS), "始信音乐", font=F_SMALL, fill=text_c)

    # 右上角小圆点（麦克风状态）
    d.ellipse(
        [x + card_w - pad - 7 * SS, y0 + 26 * SS,
         x + card_w - pad, y0 + 33 * SS],
        fill=accent_c,
    )

    # ── 中间：圆弧表盘 ──
    arc_cy = y0 + 118 * SS
    arc_r = 58 * SS
    arc_box = [cx - arc_r, arc_cy - arc_r, cx + arc_r, arc_cy + arc_r]

    # 底弧（淡）
    d.arc(arc_box, start=200, end=340,
          fill=tuple(min(255, c + 30) for c in card_c), width=2 * SS)

    # 高亮弧（主色，表示偏离基准）
    d.arc(arc_box, start=250, end=268, fill=accent_c, width=4 * SS)

    # 指针（从表盘中心向上）
    needle_len = 42 * SS
    d.line(
        [cx, arc_cy, cx - 5 * SS, arc_cy - needle_len],
        fill=accent_c, width=3 * SS,
    )
    # 指针轴心
    d.ellipse([cx - 5 * SS, arc_cy - 5 * SS, cx + 5 * SS, arc_cy + 5 * SS],
              fill=accent_c)

    # ── 音名（大字，放在表盘下方）──
    d.text((cx, arc_cy + 76 * SS), "A", font=F_NOTE, fill=text_c, anchor="mm")

    # 音分
    d.text((cx, arc_cy + 106 * SS), "+2 cents", font=F_CENTS, fill=accent_c,
           anchor="mm")

    # ── 底部：乐器按钮 ──
    btn_y = y0 + card_h - 46 * SS
    labels = ["吉他", "尤克里里", "钢琴"]
    total_w = card_w - pad * 2
    each = total_w // 3
    btn_gap = 4 * SS

    for i, lab in enumerate(labels):
        bx = x + pad + i * each
        bw = each - btn_gap
        active = (i == 0)

        if active:
            d.rounded_rectangle(
                [bx, btn_y, bx + bw, btn_y + 26 * SS],
                radius=8 * SS,
                fill=tuple(int(c * 0.22 + card_c[j] * 0.78)
                           for j, c in enumerate(accent_rgb)),
                outline=accent_c, width=SS,
            )
            fc = text_c
        else:
            d.rounded_rectangle(
                [bx, btn_y, bx + bw, btn_y + 26 * SS],
                radius=8 * SS,
                fill=card_c,
                outline=tuple(min(255, c + 18) for c in card_c), width=SS,
            )
            fc = tuple(int(c * 0.6 + card_c[j] * 0.4)
                       for j, c in enumerate(text_c))

        d.text((bx + bw // 2, btn_y + 13 * SS), lab,
               font=F_SMALL, fill=fc, anchor="mm")


# ── 逐个绘制 ──
for i, (name, bg, card, accent, accent_rgb, text) in enumerate(SCHEMES):
    col = i % COLS
    row = i // COLS
    x = (PAD + col * (CARD_W + GAP)) * SS
    y = (PAD + row * (CARD_H + TITLE_H + GAP)) * SS
    draw_scheme(x, y, name, bg, card, accent, accent_rgb, text)
# 缩小
final = img.resize((W, H), Image.LANCZOS)
os.makedirs(os.path.dirname(OUT), exist_ok=True)
final.save(OUT, "PNG", optimize=True)

print(f"✓ 已生成：{OUT}")
print(f"  尺寸：{W} × {H}")
print(f"  大小：{os.path.getsize(OUT):,} 字节")
print()


# ── 同时输出一份可直接抄的色号表 ──
print("可以直接抄的色号：")
print()
print(f"  {'方案':<14} {'--bg':<10} {'--surface':<11} {'--accent':<10} {'--text':<10}")
print("  " + "─" * 58)
for name, bg, card, accent, rgb, text in SCHEMES:
    print(f"  {name:<14} {bg:<10} {card:<11} {accent:<10} {text:<10}")

print()
print("（改 web/index.html 第 10-24 行的 :root{} 区块）")
print()
