#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
节拍器底部调整预览（临时出图工具）。

生成一张对比图：
  左 = 现在（正在跑的版本）
  右 = 调整后（待用户确认）：拍点放大、音量条放大、整组上移

只写一张 PNG 到项目根目录，不改动任何其它文件。
"""

import os
from PIL import Image, ImageDraw, ImageFont

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
OUT = os.path.join(BASE, "节拍器调整预览.png")

SS = 3
PHONE_W, PHONE_H = 390, 780
GAP, PAD = 46, 40
TITLE_H, NOTE_H = 54, 56

C = {
    "bg":       "#0a0a0a",
    "surface2": "#1f1f1f",
    "surface3": "#2b2b2b",
    "text":     "#f0f0f0",
    "text2":    "#909090",
    "text3":    "#5e5e5e",
    "accent":   "#a0a0a0",
    "border":   "#333333",
}


def hc(c):
    c = c.lstrip("#")
    return tuple(int(c[i:i + 2], 16) for i in (0, 2, 4))


def blend_on(bg, color, alpha):
    b, c = hc(bg), hc(color)
    return tuple(int(b[i] * (1 - alpha) + c[i] * alpha) for i in range(3))


img = Image.new(
    "RGB",
    ((PHONE_W * 2 + GAP + PAD * 2) * SS, (PHONE_H + TITLE_H + NOTE_H + PAD * 2) * SS),
    hc("#151515"),
)
d = ImageDraw.Draw(img)


def P(v):
    return int(round(v * SS))


def font(size):
    for p in ("/System/Library/Fonts/PingFang.ttc",
              "/System/Library/Fonts/STHeiti Light.ttc",
              "/Library/Fonts/Arial Unicode.ttf"):
        if os.path.isfile(p):
            try:
                return ImageFont.truetype(p, P(size))
            except Exception:
                pass
    return ImageFont.load_default()


F = {
    "h1":     font(16),
    "brand":  font(14),
    "brand2": font(8),
    "tab":    font(11),
    "meter":  font(12),
    "bpm":    font(105),
    "term":   font(13),
    "tag":    font(13),
    "note":   font(11),
}


def draw_glow_dot(cx, cy, r):
    """亮起的拍点：自带光晕。"""
    for i in range(9, 0, -1):
        t = i / 9
        rr = r * (1 + 2.8 * t)
        a = 0.52 * (1 - t) ** 1.7
        if a < 0.012:
            continue
        d.ellipse([P(cx - rr), P(cy - rr), P(cx + rr), P(cy + rr)],
                  fill=blend_on(C["bg"], C["accent"], a))
    d.ellipse([P(cx - r), P(cy - r), P(cx + r), P(cy + r)], fill=hc(C["accent"]))


def draw_dot(cx, cy, r):
    d.ellipse([P(cx - r), P(cy - r), P(cx + r), P(cy + r)], fill=hc(C["surface3"]))


def speaker(cx, cy, size, color, lw, waves):
    """小喇叭图标（描边风格）。"""
    s = size
    pts = [
        (cx - s * 0.42, cy - s * 0.19),
        (cx - s * 0.13, cy - s * 0.19),
        (cx + s * 0.19, cy - s * 0.46),
        (cx + s * 0.19, cy + s * 0.46),
        (cx - s * 0.13, cy + s * 0.19),
        (cx - s * 0.42, cy + s * 0.19),
    ]
    d.line([(P(x), P(y)) for x, y in pts] + [(P(pts[0][0]), P(pts[0][1]))],
           fill=color, width=P(lw), joint="curve")
    for i in range(waves):
        rr = s * (0.40 + i * 0.30)
        bx = cx + s * 0.19
        d.arc([P(bx - rr), P(cy - rr), P(bx + rr), P(cy + rr)],
              start=-54, end=54, fill=color, width=P(lw))


def draw_volume(cx, cy, cfg):
    """音量条：左小喇叭 —— 滑杆 —— 右大喇叭。"""
    total = cfg["vol_w"]
    icon = cfg["vol_icon"]
    x0 = cx - total / 2

    speaker(x0 + icon / 2, cy, icon, hc(C["text3"]), 1.5, 1)
    speaker(x0 + total - icon / 2, cy, icon, hc(C["text3"]), 1.5, 2)

    pad = icon / 2 + 9
    sx0 = x0 + pad
    sx1 = x0 + total - pad
    tr = cfg["vol_track"] / 2
    mid = sx0 + (sx1 - sx0) * 0.70

    d.rounded_rectangle([P(sx0), P(cy - tr), P(mid), P(cy + tr)],
                        radius=P(tr), fill=hc(C["accent"]))
    d.rounded_rectangle([P(mid), P(cy - tr), P(sx1), P(cy + tr)],
                        radius=P(tr), fill=hc(C["surface3"]))

    th = cfg["vol_thumb"] / 2
    d.ellipse([P(mid - th), P(cy - th), P(mid + th), P(cy + th)],
              fill=hc(C["text"]))


def draw_phone(ox, oy, cfg, tag):
    d.rectangle([P(ox), P(oy), P(ox + PHONE_W), P(oy + PHONE_H)], fill=hc(C["bg"]))

    d.text((P(ox + PHONE_W / 2), P(oy - TITLE_H + 16)), tag,
           font=F["tag"], fill=hc("#d8d8d8"), anchor="mm")

    pad = 22
    lx = ox + pad

    hy = oy + 24
    cx, cy, r = lx + 17, hy + 17, 15
    d.ellipse([P(cx - r), P(cy - r), P(cx + r), P(cy + r)],
              outline=hc(C["accent"]), width=P(1.5))
    for dx, hh, alpha in [(-5, 6.5, 0.5), (0, 11, 1.0), (5, 8.5, 0.7)]:
        x = cx + dx
        d.rounded_rectangle([P(x - 1.1), P(cy + 5 - hh), P(x + 1.1), P(cy + 5)],
                            radius=P(1.1), fill=blend_on(C["bg"], C["accent"], alpha))

    d.text((P(lx + 45), P(hy + 6)), "始信音乐", font=F["brand"], fill=hc(C["text"]))
    d.text((P(lx + 45), P(hy + 27)), "SHIXIN MUSIC", font=F["brand2"], fill=hc(C["text3"]))

    tw, th_, gap_in = 58, 28, 4
    tx, ty = lx + 124, hy + 3
    total_w = tw * 2 + gap_in * 2 + 4
    d.rounded_rectangle([P(tx), P(ty), P(tx + total_w), P(ty + th_)],
                        radius=P(9), fill=hc(C["surface2"]))
    sx = P(tx + 2 + tw + gap_in)
    d.rounded_rectangle([P(sx), P(ty + 3), P(sx + tw), P(ty + th_ - 3)],
                        radius=P(7), fill=hc(C["surface3"]))
    d.text((P(tx + 2 + tw / 2), P(ty + th_ / 2)), "调音", font=F["tab"],
           fill=hc(C["text3"]), anchor="mm")
    d.text((P(sx + tw / 2), P(ty + th_ / 2)), "节拍", font=F["tab"],
           fill=hc(C["text"]), anchor="mm")

    gx, gy = ox + PHONE_W - pad - 17, hy + 17
    d.ellipse([P(gx - 9), P(gy - 9), P(gx + 9), P(gy + 9)],
              outline=hc(C["text2"]), width=P(1.5))
    d.ellipse([P(gx - 3.5), P(gy - 3.5), P(gx + 3.5), P(gy + 3.5)],
              outline=hc(C["text2"]), width=P(1.2))

    my = oy + 82
    bw, bh = 78, 38
    bx = ox + PHONE_W - pad - bw
    d.rounded_rectangle([P(bx), P(my), P(bx + bw), P(my + bh)],
                        radius=P(10), fill=hc(C["surface2"]),
                        outline=hc(C["border"]), width=P(1))
    d.text((P(bx + 14), P(my + bh / 2)), "4/4", font=F["meter"],
           fill=hc(C["text"]), anchor="lm")
    ax, ay = bx + bw - 18, my + bh / 2 - 2
    d.line([P(ax - 4), P(ay), P(ax), P(ay + 4)], fill=hc(C["text3"]), width=P(1.6))
    d.line([P(ax), P(ay + 4), P(ax + 4), P(ay)], fill=hc(C["text3"]), width=P(1.6))

    rd = 310
    rcx = ox + PHONE_W / 2
    rcy = oy + cfg["ring_cy"]
    rx = P(rcx - rd / 2)
    ry = P(rcy - rd / 2)
    box = [rx, ry, rx + P(rd), ry + P(rd)]

    d.ellipse(box, outline=hc(C["surface3"]), width=P(2))
    ratio = (120 - 30) / (250 - 30)
    d.arc(box, start=135, end=135 + 270 * ratio,
          fill=blend_on(C["bg"], C["accent"], 0.5), width=P(3))

    d.text((P(rcx), P(rcy - 18)), "120", font=F["bpm"],
           fill=hc(C["accent"]), anchor="mm")
    d.text((P(rcx), P(rcy + 60)), "Moderato", font=F["term"],
           fill=blend_on(C["bg"], C["accent"], 0.75), anchor="mm")

    # 拍点
    dy = oy + cfg["dots_cy"]
    step = cfg["dot_r"] * 2 + cfg["dot_gap"]
    n = 4
    start = rcx - (n - 1) * step / 2
    for i in range(n):
        x = start + i * step
        if i == 0:
            draw_glow_dot(x, dy, cfg["dot_accent_r"])
        else:
            draw_dot(x, dy, cfg["dot_r"])

    # 音量条
    draw_volume(rcx, oy + cfg["vol_cy"], cfg)


NOW = {
    "ring_cy":      382,
    "dots_cy":      715,
    "dot_r":        5.0,
    "dot_accent_r": 6.25,
    "dot_gap":      9,
    "vol_cy":       746,
    "vol_w":        249,
    "vol_icon":     17,
    "vol_track":    3,
    "vol_thumb":    14,
}

NEW = {
    "ring_cy":      354,
    "dots_cy":      662,
    "dot_r":        6.5,
    "dot_accent_r": 8.0,
    "dot_gap":      12,
    "vol_cy":       696,
    "vol_w":        291,
    "vol_icon":     22,
    "vol_track":    4.5,
    "vol_thumb":    19,
}

draw_phone(PAD, PAD + TITLE_H, NOW, "现在")
draw_phone(PAD + PHONE_W + GAP, PAD + TITLE_H, NEW, "调整后")

d.text((P(PAD), P(14)), "节拍器 · 底部区域调整预览", font=F["h1"], fill=hc("#e8e8e8"))

ny = PAD + TITLE_H + PHONE_H + 18
lines = [
    "拍点    10px → 13px（间距 9 → 12px）",
    "音量条  图标 17 → 22px · 轨道 3 → 4.5px · 滑块 14 → 19px · 宽 72% → 84%",
    "整体上移 48px —— 底部留白从约 3px 增加到约 50px，不再贴着屏幕底边",
]
for i, line in enumerate(lines):
    d.text((P(PAD), P(ny + i * 17)), line, font=F["note"], fill=hc("#8a8a8a"))

final = img.resize((img.width // SS, img.height // SS), Image.LANCZOS)
final.save(OUT, "PNG", optimize=True)

print(f"✓ 已生成：{OUT}")
print(f"  尺寸：{final.width} × {final.height}")
print(f"  大小：{os.path.getsize(OUT):,} 字节")
