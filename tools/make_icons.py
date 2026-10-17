#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成「始信音乐 · 调音器」App 全套图标。

图形：双叶（AI 风格抽象叶）
  · 大尺寸 → 分叉枝版：两片叶 + 中间分叉的枝丫（有「生长」的隐喻，细节值得）
  · 小尺寸 → 水滴叶版：两片叶 + 一道托弧，去掉枝，保证 16/24px 下不糊

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
    import numpy as np
except ImportError:
    sys.exit("需要 Pillow 和 numpy：python3 -m pip install Pillow numpy")

# ---------- 配色（与网页 CSS 变量一致） ----------
GOLD       = (212, 165, 116)   # --accent  #d4a574
GOLD_LIGHT = (232, 193, 151)   # #e8c197
BG_DARK    = (14, 12, 10)      # --bg      #0e0c0a
BG_MID     = (27, 24, 21)      # #1b1815

LEAF_TOP   = (252, 236, 205)   # 叶尖高光 #fceccd
LEAF_MID   = (238, 200, 138)   # 亮金     #eec88a
ROOT_DARK  = (186, 139, 92)    # 叶根暗部
STEM_DARK  = (176, 130, 84)    # 枝的暗部 / 托弧

SS = 4  # 超采样倍数，先画大图再缩小，得到平滑边缘

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANDROID_RES = os.path.join(BASE, "android", "app", "src", "main", "res")
WEB_ICONS   = os.path.join(BASE, "web", "icons")

# 各密度的图标边长（dp -> px）
TRADITIONAL = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
ADAPTIVE    = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}

# 低于这个像素边长就用简版（水滴叶，无枝）。
# 64 及以上用带枝版：64px 下枝宽约 2.3px 仍清晰，而水滴叶在小尺寸像「笑脸」。
SIMPLE_BELOW = 64

DESIGN = 240.0   # 设计坐标系边长，中心 (120,120)


# ══════════════════════════════════════════════════════════
#  几何工具
# ══════════════════════════════════════════════════════════

def _cubic(p0, p1, p2, p3, n=48):
    """三次贝塞尔采样，返回点列（不含起点）。"""
    out = []
    for i in range(1, n + 1):
        t = i / float(n)
        mt = 1.0 - t
        a, b, c, d = mt * mt * mt, 3 * mt * mt * t, 3 * mt * t * t, t * t * t
        out.append((a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1]))
    return out


def _quad(p0, p1, p2, n=40):
    """二次贝塞尔采样，返回点列（不含起点）。"""
    out = []
    for i in range(1, n + 1):
        t = i / float(n)
        mt = 1.0 - t
        out.append((mt * mt * p0[0] + 2 * mt * t * p1[0] + t * t * p2[0],
                    mt * mt * p0[1] + 2 * mt * t * p1[1] + t * t * p2[1]))
    return out


def _vgrad(size, c_top, c_bottom):
    """生成竖直渐变图（上→下）。"""
    strip = Image.new("RGB", (1, size))
    px = strip.load()
    for y in range(size):
        t = y / float(size - 1)
        px[0, y] = tuple(int(round(c_top[i] + (c_bottom[i] - c_top[i]) * t))
                         for i in range(3))
    return strip.resize((size, size), Image.BILINEAR).convert("RGBA")


def _shape(layer, pts, c_top, c_bottom, alpha=255):
    """用渐变填充多边形，合成到 layer 上。"""
    s = layer.size[0]
    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).polygon(pts, fill=alpha)
    filled = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    filled.paste(_vgrad(s, c_top, c_bottom), (0, 0), mask)
    return Image.alpha_composite(layer, filled)


def _stroke(layer, p0, p1, w, color, alpha=255):
    """圆头线条。"""
    s = layer.size[0]
    tmp = Image.new("RGBA", (s, s), (0, 0, 0, 0))
    d = ImageDraw.Draw(tmp)
    d.line([p0, p1], fill=color + (alpha,), width=int(round(w)))
    r = w / 2.0
    for p in (p0, p1):
        d.ellipse([p[0] - r, p[1] - r, p[0] + r, p[1] + r], fill=color + (alpha,))
    return Image.alpha_composite(layer, tmp)


def _glow(layer, center, radius, color, strength):
    """径向柔光：按到圆心的距离做平滑衰减，边界严格为 0，不留方形硬边。"""
    s = layer.size[0]
    yy, xx = np.mgrid[0:s, 0:s].astype(np.float32)
    dist = np.sqrt((xx - center[0]) ** 2 + (yy - center[1]) ** 2)
    a = np.clip(1.0 - dist / float(radius), 0.0, 1.0) ** 2
    alpha = Image.fromarray((a * strength * 255.0).astype(np.uint8), "L")
    tint = Image.new("RGBA", (s, s), color + (255,))
    tint.putalpha(alpha)
    return Image.alpha_composite(layer, tint)


# ══════════════════════════════════════════════════════════
#  两个图形
# ══════════════════════════════════════════════════════════

def _mapper(canvas_px, logo_d, dy):
    """240 设计坐标 → 画布像素坐标。dy 是竖直微调（设计单位）。"""
    k = logo_d / DESIGN
    cx = cy = canvas_px / 2.0

    def m(pt):
        return (cx + (pt[0] - 120.0) * k,
                cy + (pt[1] - 120.0 + dy) * k)

    return m, k


def draw_leaf_drop(canvas_px, logo_d):
    """A · 水滴叶：两片叶 + 一道托弧。无枝，小尺寸专用。"""
    m, k = _mapper(canvas_px, logo_d, dy=-8.0)
    layer = Image.new("RGBA", (canvas_px, canvas_px), (0, 0, 0, 0))

    # 托弧：M 62 162 Q 120 206 178 162（先画，叶片压在上面）
    arc = [m((62, 162))] + [m(p) for p in _quad((62, 162), (120, 206), (178, 162))]
    arc += [m((178, 162))]
    for a, b in zip(arc, arc[1:]):
        layer = _stroke(layer, a, b, 11 * k, STEM_DARK, 150)

    # 左叶：M 120 122 C 84 122 54 96 54 66 C 86 66 112 88 120 122 Z
    left = [m((120, 122))]
    left += [m(p) for p in _cubic((120, 122), (84, 122), (54, 96), (54, 66))]
    left += [m(p) for p in _cubic((54, 66), (86, 66), (112, 88), (120, 122))]
    layer = _shape(layer, left, LEAF_TOP, LEAF_MID)

    # 右叶：M 120 122 C 156 122 186 96 186 66 C 154 66 128 88 120 122 Z
    right = [m((120, 122))]
    right += [m(p) for p in _cubic((120, 122), (156, 122), (186, 96), (186, 66))]
    right += [m(p) for p in _cubic((186, 66), (154, 66), (128, 88), (120, 122))]
    layer = _shape(layer, right, LEAF_MID, ROOT_DARK, alpha=196)

    # 叶根处一点柔光，把两片叶接起来
    layer = _glow(layer, m((120, 126)), 26 * k, GOLD_LIGHT, 0.14)
    return layer


def draw_leaf_fork(canvas_px, logo_d):
    """I · 分叉枝：两片饱满叶 + 中间分叉的枝丫。大尺寸专用。

    叶形取自最饱满的「水滴叶」，只是把两片叶的根部分开 32 单位，
    中间让出位置给枝丫；叶尖保持在 52 / 188，整体像一株从土里长出来的芽。
    """
    m, k = _mapper(canvas_px, logo_d, dy=-18.0)
    layer = Image.new("RGBA", (canvas_px, canvas_px), (0, 0, 0, 0))

    # 枝：主干 + 左右两叉（先画，叶片压住枝的顶端）
    layer = _stroke(layer, m((120, 208)), m((120, 152)), 10 * k, STEM_DARK, 225)
    layer = _stroke(layer, m((120, 154)), m((104, 118)), 9 * k, GOLD, 240)
    layer = _stroke(layer, m((120, 154)), m((136, 118)), 9 * k, (198, 152, 104), 230)

    # 左叶：根 (104,124) → 尖 (52,64)
    left = [m((104, 124))]
    left += [m(p) for p in _cubic((104, 124), (78, 124), (54, 102), (52, 64))]
    left += [m(p) for p in _cubic((52, 64), (86, 64), (110, 94), (104, 124))]
    layer = _shape(layer, left, LEAF_TOP, LEAF_MID)

    # 右叶：根 (136,124) → 尖 (188,64)
    right = [m((136, 124))]
    right += [m(p) for p in _cubic((136, 124), (162, 124), (186, 102), (188, 64))]
    right += [m(p) for p in _cubic((188, 64), (154, 64), (130, 94), (136, 124))]
    layer = _shape(layer, right, LEAF_MID, ROOT_DARK, alpha=238)

    # 分叉处一点柔光
    layer = _glow(layer, m((120, 130)), 22 * k, GOLD_LIGHT, 0.13)
    return layer


def draw_logo(canvas_px, logo_d, simple=False):
    """按尺寸选择图形。simple=True 用无水枝版。"""
    return draw_leaf_drop(canvas_px, logo_d) if simple else draw_leaf_fork(canvas_px, logo_d)


# ══════════════════════════════════════════════════════════
#  图标组装
# ══════════════════════════════════════════════════════════

def make_full_icon(size):
    """带背景的完整图标（径向渐变 + 金色柔光 + 圆角 + 图形）。"""
    s = size * SS
    grad = Image.radial_gradient("L").resize((s, s), Image.LANCZOS)
    icon = ImageOps.colorize(grad, black=BG_MID, white=BG_DARK).convert("RGBA")

    glow_mask = ImageOps.invert(Image.radial_gradient("L").resize((s, s), Image.LANCZOS))
    glow_mask = glow_mask.point(lambda v: int(v * 0.06))
    glow = Image.new("RGBA", (s, s), GOLD)
    glow.putalpha(glow_mask)
    icon = Image.alpha_composite(icon, glow)

    mask = Image.new("L", (s, s), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, s - 1, s - 1],
                                           radius=int(s * 0.22), fill=255)
    icon.putalpha(mask)

    icon = Image.alpha_composite(icon, draw_logo(s, s * 0.97, simple=size < SIMPLE_BELOW))
    return icon.resize((size, size), Image.LANCZOS)


def make_foreground(size):
    """自适应图标前景层（透明背景）。系统只显示中间 ~72/108。"""
    s = size * SS
    fg = draw_logo(s, s * (78.0 / 108.0), simple=size < SIMPLE_BELOW)
    return fg.resize((size, size), Image.LANCZOS)


def save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return os.path.getsize(path)


def main():
    written = []

    # 1 + 2. Android
    for dens, px in TRADITIONAL.items():
        p = os.path.join(ANDROID_RES, f"mipmap-{dens}", "ic_launcher.png")
        written.append((p, save(make_full_icon(px), p)))
    for dens, px in ADAPTIVE.items():
        p = os.path.join(ANDROID_RES, f"mipmap-{dens}", "ic_launcher_foreground.png")
        written.append((p, save(make_foreground(px), p)))

    # 3. PWA
    for px, name in [(192, "icon-192.png"), (512, "icon-512.png")]:
        p = os.path.join(WEB_ICONS, name)
        written.append((p, save(make_full_icon(px), p)))

    # maskable：内容留余量，适配圆形 / 圆角裁剪
    p = os.path.join(WEB_ICONS, "icon-maskable-512.png")
    ms = 512 * SS
    m = Image.new("RGBA", (ms, ms), BG_DARK + (255,))
    m = Image.alpha_composite(m, draw_logo(ms, ms * 0.82, simple=False))
    written.append((p, save(m.resize((512, 512), Image.LANCZOS), p)))

    # favicon：小尺寸，用无水枝版
    p = os.path.join(WEB_ICONS, "favicon.png")
    written.append((p, save(make_full_icon(64), p)))

    # 预览图：两个变体 × 各尺寸，肉眼检查
    p = os.path.join(BASE, "tools", "icon-preview.png")
    sheet = Image.new("RGBA", (1080, 400), (20, 18, 16, 255))
    d = ImageDraw.Draw(sheet)
    d.text((26, 16), "FORK STEM   64px and up", fill=(212, 165, 116, 255))
    x = 26
    for px in (192, 144, 108, 72, 64):
        sheet.alpha_composite(make_full_icon(px), (x, 40))
        d.text((x + 2, 40 + px + 6), f"{px}", fill=(122, 110, 98, 255))
        x += px + 24
    d.text((26, 300), "WATER-DROP   below 64px", fill=(212, 165, 116, 255))
    x = 26
    for px in (48, 32, 24, 16):
        sheet.alpha_composite(make_full_icon(px), (x, 328))
        d.text((x + 2, 328 + 52), f"{px}", fill=(122, 110, 98, 255))
        x += 62
    written.append((p, save(sheet, p)))

    print(f"共生成 {len(written)} 个文件：")
    for path, size in written:
        print(f"  {os.path.relpath(path, BASE):<60} {size:>7,} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
