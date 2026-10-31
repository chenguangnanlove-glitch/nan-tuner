#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成「调音·节拍」全套图标。

嫩芽轮廓按选定稿（琥珀金、暖光、深色圆角方底）重绘成矢量，
再在高分辨率上栅格化，缩到各密度。不拉伸低清位图。

输出：
  Android 传统图标 / 圆形图标
  Android 自适应图标：矢量前景、深色背景、Android 13 单色层
  各密度前景位图（与矢量同一造型，透明底）
  PWA / favicon / maskable
"""

import math
import os

try:
    from PIL import Image, ImageDraw, ImageFilter
    import numpy as np
except ImportError:
    raise SystemExit("需要 Pillow 和 numpy：python3 -m pip install Pillow numpy")

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
RES = os.path.join(BASE, "android", "app", "src", "main", "res")
WEB = os.path.join(BASE, "web", "icons")

# 108 视口里的嫩芽外轮廓（选定稿对称化后抽成关键点，再拟合成光滑曲线）
PTS = [
    (20.78, 17.61),
    (25.84, 18.04),
    (31.96, 19.93),
    (36.49, 22.57),
    (40.92, 26.58),
    (45.04, 33.01),
    (47.04, 41.77),
    (48.52, 43.35),
    (53.89, 55.37),
    (59.38, 43.35),
    (58.96, 44.30),
    (60.86, 41.77),
    (62.86, 33.01),
    (66.97, 26.58),
    (71.40, 22.57),
    (75.94, 19.93),
    (82.05, 18.04),
    (87.22, 17.72),
    (86.70, 23.52),
    (85.11, 29.32),
    (80.05, 38.07),
    (72.46, 44.19),
    (62.33, 47.67),
    (56.25, 64.00),
    (56.25, 76.00),
    (56.25, 87.20),
    (55.40, 88.97),
    (54.55, 89.52),
    (53.95, 89.52),
    (53.35, 89.52),
    (52.50, 88.97),
    (51.65, 87.20),
    (51.65, 76.00),
    (51.65, 64.00),
    (45.56, 47.67),
    (35.44, 44.19),
    (27.84, 38.07),
    (22.78, 29.32),
    (21.20, 23.52),
    (20.67, 17.72),
]

# 自适应图标安全区：108 画布里直径 66 的圆。嫩芽按 0.66 缩进圆心。
ADAPTIVE_SCALE = 0.66
# maskable 的安全区大约是画面的 80%
MASKABLE_SCALE = 0.84

TRADITIONAL = {"mdpi": 48, "hdpi": 72, "xhdpi": 96, "xxhdpi": 144, "xxxhdpi": 192}
ADAPTIVE_PX = {"mdpi": 108, "hdpi": 162, "xhdpi": 216, "xxhdpi": 324, "xxxhdpi": 432}


def cubics(pts):
    p = list(pts)
    seq = [p[-1]] + p + [p[0], p[1]]
    segs = []
    for i in range(1, len(p) + 1):
        p0, p1, p2, p3 = seq[i - 1], seq[i], seq[i + 1], seq[i + 2]
        b1 = (p1[0] + (p2[0] - p0[0]) / 6.0, p1[1] + (p2[1] - p0[1]) / 6.0)
        b2 = (p2[0] - (p3[0] - p1[0]) / 6.0, p2[1] - (p3[1] - p1[1]) / 6.0)
        segs.append((p1, b1, b2, p2))
    return segs


def sample(segs, n=12):
    out = []
    for p1, b1, b2, p2 in segs:
        for k in range(n):
            t = k / float(n)
            mt = 1.0 - t
            a, b, c, d = mt ** 3, 3 * mt * mt * t, 3 * mt * t * t, t ** 3
            out.append((
                a * p1[0] + b * b1[0] + c * b2[0] + d * p2[0],
                a * p1[1] + b * b1[1] + c * b2[1] + d * p2[1],
            ))
    return out


def path_d(segs, scale=1.0):
    def xy(p):
        x = 54.0 + (p[0] - 54.0) * scale
        y = 54.0 + (p[1] - 54.0) * scale
        return f"{x:.2f},{y:.2f}"

    d = "M " + xy(segs[0][0])
    for _p1, b1, b2, p2 in segs:
        d += f" C {xy(b1)} {xy(b2)} {xy(p2)}"
    return d + " Z"


SEGS = cubics(PTS)
SPROUT_FULL = path_d(SEGS, 1.0)
SPROUT_SAFE = path_d(SEGS, ADAPTIVE_SCALE)
POLY = sample(SEGS, 14)


def _px(p, scale, size):
    x = 54.0 + (p[0] - 54.0) * scale
    y = 54.0 + (p[1] - 54.0) * scale
    return x / 108.0 * size, y / 108.0 * size


def _background(size):
    yy, xx = np.mgrid[0:size, 0:size]
    dist = np.sqrt((xx - size / 2.0) ** 2 + (yy - size * 0.42) ** 2) / (size * 0.78)
    dist = np.clip(dist, 0.0, 1.0) ** 1.05
    warm = np.array([62, 44, 30], dtype=np.float32)
    edge = np.array([14, 12, 10], dtype=np.float32)
    col = warm * (1.0 - dist)[..., None] + edge * dist[..., None]
    return Image.fromarray(
        np.dstack([col.astype(np.uint8), np.full((size, size), 255, np.uint8)]),
        "RGBA",
    )


def _sprout(size, scale):
    """透明底上的嫩芽：暖色光晕 + 金色渐变。"""
    layer = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    poly = [_px(p, scale, size) for p in POLY]

    # 叶后方的暖光
    glow = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    ImageDraw.Draw(glow).polygon(poly, fill=(244, 196, 110, 255))
    glow = glow.filter(ImageFilter.GaussianBlur(radius=max(1.2, size * 0.045)))
    arr = np.array(glow)
    arr[:, :, 3] = (arr[:, :, 3].astype(np.float32) * 0.95).astype(np.uint8)
    layer = Image.alpha_composite(layer, Image.fromarray(arr, "RGBA"))

    # 上亮下暗，右侧略深，接近选定稿的受光
    mask = Image.new("L", (size, size), 0)
    ImageDraw.Draw(mask).polygon(poly, fill=255)
    top = np.array([255, 226, 168], dtype=np.float32)
    bot = np.array([196, 128, 58], dtype=np.float32)
    grad = np.zeros((size, size, 3), dtype=np.uint8)
    shade = 0.92 + 0.08 * (1.0 - np.linspace(0.0, 1.0, size))
    for y in range(size):
        t = y / float(size - 1)
        row = top * (1.0 - t) + bot * t
        grad[y, :] = (row * shade[:, None]).astype(np.uint8)
    paint = Image.fromarray(np.dstack([grad, np.array(mask)]), "RGBA")
    return Image.alpha_composite(layer, paint)


def _mask(size, kind):
    m = Image.new("L", (size, size), 0)
    d = ImageDraw.Draw(m)
    if kind == "circle":
        d.ellipse([1, 1, size - 2, size - 2], fill=255)
    elif kind == "round":
        d.rounded_rectangle([0, 0, size - 1, size - 1], radius=int(size * 0.225), fill=255)
    else:
        d.rectangle([0, 0, size - 1, size - 1], fill=255)
    return m


def render_icon(size, scale=1.0, mask="round", master=None):
    """master 给定时从高分辨率母版缩小，避免每个尺寸重算。"""
    if master is not None and master.size[0] != size:
        img = master.resize((size, size), Image.LANCZOS)
        if mask:
            img.putalpha(_mask(size, mask))
        return img
    img = Image.alpha_composite(_background(size), _sprout(size, scale))
    if mask:
        img.putalpha(_mask(size, mask))
    return img


def render_foreground(size, scale=ADAPTIVE_SCALE):
    return _sprout(size, scale)


def save(img, path):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    img.save(path, "PNG", optimize=True)
    return os.path.getsize(path)


def write_vectors():
    fg = f"""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:aapt="http://schemas.android.com/aapt"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <!-- 暖光：跟着嫩芽一起缩进安全区，圆形遮罩裁掉也没关系 -->
    <path android:pathData="M54,36 m-22,0 a22,22 0 1,0 44,0 a22,22 0 1,0 -44,0">
        <aapt:attr name="android:fillColor">
            <gradient
                android:type="radial"
                android:centerX="54"
                android:centerY="36"
                android:gradientRadius="22"
                android:startColor="#66F0C27A"
                android:endColor="#00F0C27A" />
        </aapt:attr>
    </path>
    <path android:pathData="{SPROUT_SAFE}">
        <aapt:attr name="android:fillColor">
            <gradient
                android:type="linear"
                android:startX="32"
                android:startY="28"
                android:endX="76"
                android:endY="80"
                android:startColor="#FFF6E2B4"
                android:endColor="#FFC17E3E" />
        </aapt:attr>
    </path>
</vector>
"""
    mono = f"""<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <!-- Android 13 主题图标：只保留嫩芽剪影，颜色由系统着色 -->
    <path
        android:fillColor="#FFFFFFFF"
        android:pathData="{SPROUT_SAFE}" />
</vector>
"""
    bg = """<?xml version="1.0" encoding="utf-8"?>
<vector xmlns:android="http://schemas.android.com/apk/res/android"
    xmlns:aapt="http://schemas.android.com/aapt"
    android:width="108dp"
    android:height="108dp"
    android:viewportWidth="108"
    android:viewportHeight="108">
    <path android:pathData="M0,0h108v108h-108z">
        <aapt:attr name="android:fillColor">
            <gradient
                android:type="radial"
                android:centerX="54"
                android:centerY="46"
                android:gradientRadius="78"
                android:startColor="#FF3A2C22"
                android:endColor="#FF0E0C0A" />
        </aapt:attr>
    </path>
</vector>
"""
    adaptive = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
</adaptive-icon>
"""
    adaptive_mono = """<?xml version="1.0" encoding="utf-8"?>
<adaptive-icon xmlns:android="http://schemas.android.com/apk/res/android">
    <background android:drawable="@drawable/ic_launcher_background" />
    <foreground android:drawable="@drawable/ic_launcher_foreground" />
    <monochrome android:drawable="@drawable/ic_launcher_monochrome" />
</adaptive-icon>
"""
    files = {
        os.path.join(RES, "drawable", "ic_launcher_foreground.xml"): fg,
        os.path.join(RES, "drawable", "ic_launcher_monochrome.xml"): mono,
        os.path.join(RES, "drawable", "ic_launcher_background.xml"): bg,
        os.path.join(RES, "mipmap-anydpi-v26", "ic_launcher.xml"): adaptive,
        os.path.join(RES, "mipmap-anydpi-v26", "ic_launcher_round.xml"): adaptive,
        os.path.join(RES, "mipmap-anydpi-v33", "ic_launcher.xml"): adaptive_mono,
        os.path.join(RES, "mipmap-anydpi-v33", "ic_launcher_round.xml"): adaptive_mono,
    }
    for path, text in files.items():
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as f:
            f.write(text)
    return list(files)


def main():
    written = []
    write_vectors()

    master_round = render_icon(1024, scale=1.0, mask="round")
    master_circle = render_icon(1024, scale=1.0, mask="circle")
    master_square = render_icon(1024, scale=MASKABLE_SCALE, mask=None)
    master_fg = render_foreground(1024, scale=ADAPTIVE_SCALE)

    for dens, px in TRADITIONAL.items():
        p = os.path.join(RES, f"mipmap-{dens}", "ic_launcher.png")
        written.append((p, save(master_round.resize((px, px), Image.LANCZOS), p)))
        p = os.path.join(RES, f"mipmap-{dens}", "ic_launcher_round.png")
        written.append((p, save(master_circle.resize((px, px), Image.LANCZOS), p)))
    for dens, px in ADAPTIVE_PX.items():
        p = os.path.join(RES, f"mipmap-{dens}", "ic_launcher_foreground.png")
        written.append((p, save(master_fg.resize((px, px), Image.LANCZOS), p)))

    for px, name in ((192, "icon-192.png"), (512, "icon-512.png")):
        p = os.path.join(WEB, name)
        written.append((p, save(master_round.resize((px, px), Image.LANCZOS), p)))
    p = os.path.join(WEB, "icon-maskable-512.png")
    written.append((p, save(master_square.resize((512, 512), Image.LANCZOS), p)))
    p = os.path.join(WEB, "favicon.png")
    written.append((p, save(master_round.resize((64, 64), Image.LANCZOS), p)))

    # 仓库里的检查图：圆角方、圆、安全区前景
    sheet = Image.new("RGBA", (1080, 420), (22, 20, 18, 255))
    d = ImageDraw.Draw(sheet)
    tiles = [
        (master_round.resize((192, 192), Image.LANCZOS), "round rect"),
        (master_circle.resize((192, 192), Image.LANCZOS), "circle"),
        (master_square.resize((192, 192), Image.LANCZOS), "maskable"),
        (master_fg.resize((192, 192), Image.LANCZOS), "adaptive fg"),
    ]
    x = 36
    for im, label in tiles:
        sheet.alpha_composite(im, (x, 48))
        d.text((x, 28), label, fill=(212, 165, 116, 255))
        x += 250
    d.text((36, 270), "48 / 72 / 96 / 144 / 192", fill=(212, 165, 116, 255))
    x = 36
    for px in (48, 72, 96, 144, 192):
        sheet.alpha_composite(master_round.resize((px, px), Image.LANCZOS), (x, 300))
        x += px + 20
    prev = os.path.join(BASE, "tools", "icon-preview.png")
    written.append((prev, save(sheet, prev)))

    print(f"共生成 {len(written)} 个位图，外加矢量自适应图标：")
    for path, size in written:
        print(f"  {os.path.relpath(path, BASE):<62} {size:>7,} B")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
