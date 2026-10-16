#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
节拍器设计图。

画三个状态并列，展示最新设计：
  · 圆环加大，数字占圆环直径 1/3
  · 去掉独立播放按钮，点圆环任意位置开始/停止
  · 播放时数字变主色
  · 圆环进度弧随速度变化

配色：石墨黑（当前使用的主题）
"""

import os
import math
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "节拍器设计图.png")

SS = 3

# ── 配色（石墨黑）──
C = {
    "bg":        "#0a0a0a",
    "surface":   "#161616",
    "surface2":  "#1f1f1f",
    "surface3":  "#2b2b2b",
    "text":      "#f0f0f0",
    "text2":     "#909090",
    "text3":     "#5e5e5e",
    "accent":    "#a0a0a0",
    "border":    "#333333",
}

# ── 布局（逻辑像素）──
PHONE_W, PHONE_H = 390, 780
GAP = 34
PAD = 36
TITLE_H = 44
NOTE_H = 30


def h(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def mix(c1, c2, t):
    a, b = h(c1), h(c2)
    return tuple(int(a[i] + (b[i] - a[i]) * t) for i in range(3))


def blend_on(bg, color, alpha):
    """把 color 以 alpha 透明度叠在 bg 上。"""
    b, c = h(bg), h(color)
    return tuple(int(b[i] * (1 - alpha) + c[i] * alpha) for i in range(3))


img = Image.new("RGB", ((PHONE_W * 3 + GAP * 2 + PAD * 2) * SS,
                        (PHONE_H + TITLE_H + NOTE_H + PAD * 2 + 30) * SS),
                h("#151515"))
d = ImageDraw.Draw(img)


def P(v):
    return int(v * SS)


def font(size):
    for path in ["/System/Library/Fonts/PingFang.ttc",
                 "/System/Library/Fonts/STHeiti Light.ttc",
                 "/Library/Fonts/Arial Unicode.ttf"]:
        if os.path.isfile(path):
            try:
                return ImageFont.truetype(path, P(size))
            except Exception:
                continue
    return ImageFont.load_default()


F = {
    "title":  font(15),
    "note":   font(11),
    "brand":  font(14),
    "brand2": font(8),
    "tab":    font(11),
    "meter":  font(12),
    "bpm":    font(105),     # ← 占圆环 1/3 以上
    "bpm_s":  font(56),
    "term":   font(13),
    "hint":   font(10),
}


# ══════════════════════════════════════════════════════════
#  画一个状态
# ══════════════════════════════════════════════════════════

def draw_phone(ox, oy, title, state):
    """state: 'idle' | 'playing' | 'editing'"""

    # 屏幕背景
    d.rectangle([P(ox), P(oy), P(ox + PHONE_W), P(oy + PHONE_H)], fill=h(C["bg"]))

    inner_pad = 22

    # ── 标题（屏幕外上方）──
    d.text((P(ox), P(oy - TITLE_H + 8)), title, font=F["title"],
           fill=h("#d8d8d8"))

    # ══════════════════════════════════════════════
    #  头部
    # ══════════════════════════════════════════════
    hy = oy + 24
    lx = ox + inner_pad

    # logo
    cx, cy, r = lx + 17, hy + 17, 15
    d.ellipse([P(cx - r), P(cy - r), P(cx + r), P(cy + r)],
              outline=h(C["accent"]), width=P(1.5))
    for dx, hh, alpha in [(-5, 6.5, 0.5), (0, 11, 1.0), (5, 8.5, 0.7)]:
        x = cx + dx
        y0 = cy + 5
        y1 = y0 - hh
        d.rounded_rectangle(
            [P(x - 1.1), P(y1), P(x + 1.1), P(y0)],
            radius=P(1.1), fill=blend_on(C["bg"], C["accent"], alpha))

    # 品牌
    d.text((P(lx + 45), P(hy + 6)), "始信音乐", font=F["brand"], fill=h(C["text"]))
    d.text((P(lx + 45), P(hy + 27)), "SHIXIN MUSIC", font=F["brand2"],
           fill=h(C["text3"]))

    # 切换键（胶囊）
    tw, th = 58, 28
    tx = lx + 124
    ty = hy + 3
    gap_in = 4
    total_w = tw * 2 + gap_in * 2 + 4
    d.rounded_rectangle([P(tx), P(ty), P(tx + total_w), P(ty + th)],
                        radius=P(9), fill=h(C["surface2"]))
    # 滑块在"节拍"
    sx = tx + 2 + tw + gap_in
    d.rounded_rectangle([P(sx), P(ty + 3), P(sx + tw), P(ty + th - 3)],
                        radius=P(7), fill=h(C["surface3"]))
    d.text((P(tx + 2 + tw // 2), P(ty + th // 2)), "调音", font=F["tab"],
           fill=h(C["text3"]), anchor="mm")
    d.text((P(sx + tw // 2), P(ty + th // 2)), "节拍", font=F["tab"],
           fill=h(C["text"]), anchor="mm")

    # 设置齿轮
    gx, gy = ox + PHONE_W - inner_pad - 17, hy + 17
    d.ellipse([P(gx - 9), P(gy - 9), P(gx + 9), P(gy + 9)],
              outline=h(C["text2"]), width=P(1.5))
    d.ellipse([P(gx - 3.5), P(gy - 3.5), P(gx + 3.5), P(gy + 3.5)],
              outline=h(C["text2"]), width=P(1.2))

    # ══════════════════════════════════════════════
    #  拍号按钮（右上）
    # ══════════════════════════════════════════════
    my = oy + 82
    bw, bh = 78, 38
    bx = ox + PHONE_W - inner_pad - bw
    d.rounded_rectangle([P(bx), P(my), P(bx + bw), P(my + bh)],
                        radius=P(10), fill=h(C["surface2"]),
                        outline=h(C["border"]), width=P(1))
    d.text((P(bx + 14), P(my + bh // 2)), "4/4", font=F["meter"],
           fill=h(C["text"]), anchor="lm")
    # 箭头
    ax, ay = bx + bw - 18, my + bh // 2 - 2
    d.line([P(ax - 4), P(ay), P(ax), P(ay + 4)], fill=h(C["text3"]),
           width=P(1.6))
    d.line([P(ax), P(ay + 4), P(ax + 4), P(ay)], fill=h(C["text3"]),
           width=P(1.6))

    # ══════════════════════════════════════════════
    #  圆环
    # ══════════════════════════════════════════════
    ring_d = 310
    ring_cx = ox + PHONE_W // 2
    # 圆环垂直位置：给下方拍点留出空间
    area_top = my + bh + 16
    area_bottom = oy + PHONE_H - 84
    ring_cy = (area_top + area_bottom) // 2

    rx = P(ring_cx - ring_d // 2)
    ry = P(ring_cy - ring_d // 2)
    rbox = [rx, ry, rx + P(ring_d), ry + P(ring_d)]
    sw = P(2)

    # 底圈
    d.ellipse(rbox, outline=h(C["surface3"]), width=sw)

    # 进度弧：270°，从 135° 开始
    bpm = 120
    ratio = (bpm - 30) / (250 - 30)
    arc_deg = 270 * ratio
    d.arc(rbox, start=135, end=135 + arc_deg,
          fill=blend_on(C["bg"], C["accent"], 0.5), width=P(3))

    # ── 圆心内容 ──
    num_cy = ring_cy - 18          # 数字的垂直中心（两个状态统一）

    if state == "editing":
        # 输入框：中心和数字对齐
        iw, ih = 250, 112
        ix = ring_cx - iw // 2
        iy = num_cy - ih // 2
        d.rounded_rectangle([P(ix), P(iy), P(ix + iw), P(iy + ih)],
                            radius=P(16), fill=h(C["surface2"]),
                            outline=h(C["accent"]), width=P(2))
        d.text((P(ring_cx - 6), P(iy + ih // 2)), "8",
               font=F["bpm"], fill=h(C["accent"]), anchor="mm")
        # 光标
        d.rectangle([P(ring_cx + 34), P(iy + 22),
                     P(ring_cx + 37), P(iy + ih - 22)],
                    fill=h(C["accent"]))
        d.text((P(ring_cx), P(num_cy + 78)), "Moderato", font=F["term"],
               fill=h(C["text3"]), anchor="mm")
    else:
        playing = (state == "playing")
        num_color = C["accent"] if playing else C["text"]

        # 数字（占圆环直径 1/3）
        d.text((P(ring_cx), P(num_cy)), "120", font=F["bpm"],
               fill=h(num_color), anchor="mm")

        # 术语
        term_color = blend_on(C["bg"], C["accent"], 0.75) if playing else C["text3"]
        d.text((P(ring_cx), P(num_cy + 78)), "Moderato", font=F["term"],
               fill=term_color, anchor="mm")

        # 播放时脉冲环（刚扩散出去的那个）
        if playing:
            d.ellipse([rx + P(8), ry + P(8),
                       rx + P(ring_d) - P(8), ry + P(ring_d) - P(8)],
                      outline=blend_on(C["bg"], C["accent"], 0.28), width=P(2))

    # ══════════════════════════════════════════════
    #  拍点（紧跟圆环下方）
    # ══════════════════════════════════════════════
    dy = ring_cy + ring_d // 2 + 34
    dot_r = 5.5
    spacing = 24
    n = 4
    start = ring_cx - (n - 1) * spacing / 2

    for i in range(n):
        x = start + i * spacing
        rr = dot_r * (1.25 if i == 0 else 1.0)
        if state == "playing" and i == 0:
            d.ellipse([P(x - rr), P(dy - rr), P(x + rr), P(dy + rr)],
                      fill=h(C["accent"]))
        else:
            d.ellipse([P(x - rr), P(dy - rr), P(x + rr), P(dy + rr)],
                      fill=h(C["surface3"]))

    # ══════════════════════════════════════════════
    #  底部说明
    # ══════════════════════════════════════════════
    notes = {
        "idle":    "点圆环任意位置 → 开始",
        "playing": "数字变主色 = 运行中\n再点一下 → 停止",
        "editing": "点数字 → 直接输入速度\n回车确认",
    }
    ny = oy + PHONE_H + 14
    for i, line in enumerate(notes[state].split("\n")):
        d.text((P(ox + PHONE_W // 2), P(ny + i * 16)), line,
               font=F["note"], fill=h("#8a8a8a"), anchor="mm")


# ══════════════════════════════════════════════════════════
#  绘制三个状态
# ══════════════════════════════════════════════════════════

positions = [
    ("停止", "idle"),
    ("运行中", "playing"),
    ("输入速度", "editing"),
]

for i, (title, state) in enumerate(positions):
    ox = PAD + i * (PHONE_W + GAP)
    oy = PAD + TITLE_H
    draw_phone(ox, oy, title, state)

# ── 顶部总标题 ──
d.text((P(PAD), P(10)), "节拍器设计 · 点圆环即开始（去掉独立播放按钮）",
       font=F["title"], fill=h("#e0e0e0"))

# ── 底部尺寸说明 ──
d.text((P(PAD), P(PAD * 2 + PHONE_H + TITLE_H + NOTE_H + 16)),
       "圆环 310px  ·  数字 105px（占 1/3）  ·  术语在数字下方",
       font=F["note"], fill=h("#7a7a7a"))

# ── 尺寸标注（只在第一个手机上画简洁的引线）──
ox, oy = PAD, PAD + TITLE_H
ring_d = 310
ring_cx = ox + PHONE_W // 2
my = oy + 82
area_top = my + 38 + 16
area_bottom = oy + PHONE_H - 84
ring_cy = (area_top + area_bottom) // 2
num_cy = ring_cy - 18
num_h = 97

ring_left = ring_cx - ring_d // 2
ring_right = ring_cx + ring_d // 2
ring_top = ring_cy - ring_d // 2

BLUE = h("#5a8fd8")

# ── 圆环直径：竖线画在圆环左侧外部 ──
x0 = ring_left - 16
d.line([P(x0), P(ring_top), P(x0), P(ring_cy + ring_d // 2)],
       fill=BLUE, width=P(1.4))
for y in (ring_top, ring_cy + ring_d // 2):
    d.line([P(x0 - 5), P(y), P(x0 + 5), P(y)], fill=BLUE, width=P(1.4))
d.text((P(x0 - 9), P(ring_cy)), "310", font=F["hint"],
       fill=BLUE, anchor="rm")

# ── 数字高度：紧贴数字左侧 ──
x1 = ring_cx - 100
d.line([P(x1), P(num_cy - num_h // 2), P(x1), P(num_cy + num_h // 2)],
       fill=BLUE, width=P(1.4))
for y in (num_cy - num_h // 2, num_cy + num_h // 2):
    d.line([P(x1 - 5), P(y), P(x1 + 5), P(y)], fill=BLUE, width=P(1.4))
d.text((P(x1 - 9), P(num_cy)), "105", font=F["hint"],
       fill=BLUE, anchor="rm")

# ── 保存 ──
final = img.resize((img.width // SS, img.height // SS), Image.LANCZOS)
final.save(OUT, "PNG", optimize=True)

print(f"✓ 已生成：{OUT}")
print(f"  尺寸：{final.width} × {final.height}")
print(f"  大小：{os.path.getsize(OUT):,} 字节")
print()
print(f"  数字 105px ÷ 圆环 310px = {105/310*100:.1f}%")
