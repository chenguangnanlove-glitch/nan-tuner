#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成「始信音乐 · 调音器」App 全套图标。

素材来源：网页 index tuner.html 里的内联 SVG logo（音叉/音柱图形）。
输出：
  1. Android 传统图标  android/app/src/main/res/mipmap-*/ic_launcher.png
  2. Android 自适应图标前景  android/app/src/main/res/mipmap-*/ic_launcher_foreground.png
  3. PWA 图标  web/icons/*.png

可反复运行，覆盖生成，不改动其它文件。
"""

import os
import sys

try:
    from PIL import Image, ImageDraw, ImageOps
except ImportError:
    sys.exit("需要 Pillow：python3 -m pip install Pillow")

# ---------- 配色（与网页 CSS 变量一致） ----------
GOLD       = (212, 165, 116)   # --accent  #d4a574
GOLD_LIGHT = (232, 193, 151)   # #e8c197
BG_DARK    = (14, 12, 10)      # --bg      #0e0c0a
BG_MID     = (34, 31, 27)      # #221f1b

SS = 4  # 超采样倍数，先画大图再缩小，得到平滑边缘

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANDROID_RES = os.path.join(BASE, "android", "app", "src", "main", "res")
WEB_ICONS   = os.path.join(BASE, "web", "icons")

# 各密度的图标边长（dp -> px）
TRADITIONAL = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
ADAPTIVE    = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}


def draw_logo(canvas_px, logo_d):
    """在透明图层中央绘制 logo，返回 RGBA 图层。

    几何完全复刻网页 SVG（viewBox 32x32，外圆 r=14.25，直径 28.5）。
    logo_d —— logo 外圆直径（像素）
    """
    layer = Image.new("RGBA", (canvas_px, canvas_px), (0, 0, 0, 0))
    d = ImageDraw.Draw(layer)
    cx = cy = canvas_px / 2.0

    # --- 外圆环 ---
    r = logo_d / 2.0
    ring_w = max(1, int(round(logo_d * (1.5 / 28.5))))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], outline=GOLD + (255,), width=ring_w)

    # --- 三根音柱（宽度/间距/底部基线均按原 SVG 比例） ---
    bar_w  = logo_d * (2.2 / 28.5)
    gap    = logo_d * (5.4 / 28.5)
    bottom = cy + logo_d * (5.5 / 28.5)
    specs = [
        (-1, 6.5 / 28.5, 128),   # 左柱，opacity .5
        ( 0, 11.0 / 28.5, 255),  # 中柱，实心
        ( 1, 8.5 / 28.5, 179),   # 右柱，opacity .7
    ]
    for side, h_ratio, alpha in specs:
        xc = cx + side * gap
        h  = logo_d * h_ratio
        d.rounded_rectangle(
            [xc - bar_w / 2, bottom - h, xc + bar_w / 2, bottom],
            radius=bar_w / 2, fill=GOLD + (alpha,),
        )
    return layer


def make_full_icon(size):
    """生成带背景的完整图标（圆角方形 + 径向渐变 + 金色柔光 + logo）。"""
    s = size * SS
    # 径向渐变背景：中心稍亮，边缘更深
    grad = Image.radial_gradient("L").resize((s, s), Image.LANCZOS)
    icon = ImageOps.colorize(grad, black=BG_MID, white=BG_DARK).convert("RGBA")

    # 中心叠一层极淡的金色光晕
    glow_mask = ImageOps.invert(Image.radial_gradient("L").resize((s, s), Image.LANCZOS))
    glow_mask = glow_mask.point(lambda v: int(v * 0.10))
    glow = Image.new("RGBA", (s, s), GOLD)
    glow.putalpha(glow_mask)
    icon = Image.alpha_composite(icon, glow)

    # 圆角遮罩
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1], radius=int(s * 0.22), fill=255)
    icon.putalpha(mask)

    # 叠加 logo
    icon = Image.alpha_composite(icon, draw_logo(s, s * 0.66))
    return icon.resize((size, size), Image.LANCZOS)


def make_foreground(size):
    """生成自适应图标的前景层（透明背景）。

    108dp 画布中，系统只显示中间约 72dp，安全区为直径 66dp 的圆。
    logo 直径取 60/108，确保任何厂商遮罩下都不被裁到。
    """
    s = size * SS
    fg = draw_logo(s, s * (60.0 / 108.0))
    return fg.resize((size, size), Image.LANCZOS)


def save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return os.path.getsize(path)


def main():
    written = []

    # 1 + 2. Android 图标
    for dens, px in TRADITIONAL.items():
        p = os.path.join(ANDROID_RES, f"mipmap-{dens}", "ic_launcher.png")
        written.append((p, save(make_full_icon(px), p)))
    for dens, px in ADAPTIVE.items():
        p = os.path.join(ANDROID_RES, f"mipmap-{dens}", "ic_launcher_foreground.png")
        written.append((p, save(make_foreground(px), p)))

    # 3. PWA 图标
    for px, name in [(192, "icon-192.png"), (512, "icon-512.png")]:
        p = os.path.join(WEB_ICONS, name)
        written.append((p, save(make_full_icon(px), p)))
    # maskable：内容留更多余量，适配圆形/圆角裁剪
    p = os.path.join(WEB_ICONS, "icon-maskable-512.png")
    ms = 512 * SS
    m = Image.new("RGBA", (ms, ms), BG_DARK + (255,))
    m = Image.alpha_composite(m, draw_logo(ms, ms * 0.50))
    written.append((p, save(m.resize((512, 512), Image.LANCZOS), p)))
    p = os.path.join(WEB_ICONS, "favicon.png")
    written.append((p, save(make_full_icon(64), p)))

    # 预览图（方便肉眼检查）
    p = os.path.join(BASE, "tools", "icon-preview.png")
    sheet = Image.new("RGBA", (760, 300), (24, 22, 20, 255))
    x = 30
    for px in (192, 144, 108, 72, 48):
        sheet.alpha_composite(make_full_icon(px), (x, 40))
        x += px + 24
    sheet.alpha_composite(make_foreground(160), (x, 56))
    written.append((p, save(sheet, p)))

    print(f"共生成 {len(written)} 个文件：")
    for path, size in written:
        print(f"  {os.path.relpath(path, BASE):<58} {size:>7,} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
