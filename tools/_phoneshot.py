#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机视口完整截图器。

难点：这台机器的 Chrome 忽略 --window-size，截图高度只有 ~470px，
而手机视口高 780px —— 一次拍不全。

做法：把同一个 390×780 的页面拍成上下两段（第二段用负 margin 上移），
再用 PIL 垂直拼成完整的 390×780 图。

用法：
    python3 tools/_phoneshot.py <页面文件> <输出png>
"""

import io
import os
import subprocess
import sys
import time

from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

VW, VH = 390, 780          # 手机视口
SEG = 380                  # 每段高度（留余量，避免被浏览器 UI 吃掉）

WRAP = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  html,body{{margin:0;padding:0;background:#000;overflow:hidden}}
  .clip{{width:{vw}px;height:{seg}px;overflow:hidden;position:relative}}
  iframe{{width:{vw}px;height:{vh}px;border:0;display:block;
         position:absolute;left:0;top:-{off}px}}
</style></head>
<body><div class="clip"><iframe src="{src}"></iframe></div></body></html>
"""


def shot(url_file, out_png, off):
    wrap = WRAP.format(vw=VW, vh=VH, seg=SEG, off=off,
                       src="file://" + url_file)
    # 每段用独立文件名，避免上一轮的 Chrome 还占着
    wrap_path = os.path.join(SHOT, "_seg%d.html" % off)
    io.open(wrap_path, "w", encoding="utf-8").write(wrap)

    prof = os.path.join(SHOT, "_prof%d" % off)
    png = os.path.join(SHOT, "_seg%d.png" % off)
    if os.path.exists(png):
        os.remove(png)

    subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--disable-crash-reporter", "--no-first-run", "--hide-scrollbars",
         "--allow-file-access-from-files",
         "--user-data-dir=" + prof,
         "--virtual-time-budget=2500",
         "--screenshot=" + png,
         "file://" + wrap_path],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

    for _ in range(20):
        time.sleep(2)
        if os.path.exists(png) and os.path.getsize(png) > 5000:
            return png
    return None


def main():
    if len(sys.argv) < 3:
        sys.exit("用法: _phoneshot.py <页面文件> <输出png>")
    page = os.path.abspath(sys.argv[1])
    out = os.path.abspath(sys.argv[2])

    segs = []
    for i, off in enumerate((0, SEG)):
        p = shot(page, out, off)
        if not p:
            sys.exit("第 %d 段截图失败" % (i + 1))
        segs.append(Image.open(p).copy())
        print("  第 %d 段 ok" % (i + 1))

    # 裁成统一宽度并拼接
    parts = []
    for s in segs:
        w = min(s.width, VW)
        parts.append(s.crop((0, 0, w, min(s.height, SEG))))

    total_h = sum(p.height for p in parts)
    canvas = Image.new("RGB", (VW, total_h), (0, 0, 0))
    y = 0
    for p in parts:
        canvas.paste(p, (0, y))
        y += p.height

    canvas = canvas.crop((0, 0, VW, min(total_h, VH)))
    canvas.save(out)
    print("已生成", out, canvas.size)


if __name__ == "__main__":
    main()
