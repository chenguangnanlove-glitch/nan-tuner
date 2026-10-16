#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
多尺寸检查：在几个常见手机高度下，看两页是否都不溢出、
且底部边界是否一致。

对每个尺寸输出：
  调音页 内容高 / 是否溢出
  节拍页 内容高 / 是否溢出
  两者末尾元素底部的差值
"""

import io
import os
import subprocess
import sys
import time

from PIL import Image

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
SRC = os.path.join(BASE, "web", "index.html")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

SIZES = [(390, 844), (390, 780), (375, 667), (412, 915), (360, 640)]

MEASURE = """
<script>
(function(){
  var lines = [];
  function snap(label, h){
    var pt = document.getElementById('pageTuner');
    var pm = document.getElementById('pageMetro');
    var active = document.body.dataset.page === 'metro' ? pm : pt;
    var last = active.querySelector('.hint');
    var r = active.getBoundingClientRect();
    var lr = last ? last.getBoundingClientRect() : null;
    lines.push(label + ' 底部=' + (lr ? Math.round(lr.bottom) : '-') +
               ' 内容高=' + Math.round(r.height) +
               ' 溢出=' + (r.bottom > h + 1 ? 'YES' : 'no'));
  }
  window.addEventListener('load', function(){
    setTimeout(function(){
      var h = window.innerHeight;
      snap('调音页', h);
      var tab = document.getElementById('tabMetro');
      if (tab) tab.click();
      setTimeout(function(){
        snap('节拍页', h);
        var d = document.createElement('div');
        d.id = 'R';
        d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
          'background:#000;color:#0f0;font:12px/1.5 monospace;padding:6px;white-space:pre';
        d.textContent = 'viewport ' + window.innerWidth + 'x' + h + '\\n' + lines.join('\\n');
        document.body.appendChild(d);
      }, 400);
    }, 350);
  });
})();
</script>
"""


def build(w, h):
    html = io.open(SRC, encoding="utf-8").read()
    html = html.replace("</body>", MEASURE + "</body>", 1)
    tgt = os.path.join(SHOT, "multi_in.html")
    io.open(tgt, "w", encoding="utf-8").write(html)

    wrap = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}
.c{width:%dpx;height:%dpx;overflow:hidden;position:relative}
iframe{width:%dpx;height:%dpx;border:0;display:block;position:absolute;left:0;top:0}
</style></head><body><div class="c"><iframe src="file://%s"></iframe></div></body></html>""" % (
        w, h, w, h, tgt)
    wp = os.path.join(SHOT, "multi_wrap.html")
    io.open(wp, "w", encoding="utf-8").write(wrap)
    return wp


def shoot(wp, out, tag):
    if os.path.exists(out):
        os.remove(out)
    prof = os.path.join(SHOT, "_mp_" + tag)
    subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--disable-crash-reporter", "--no-first-run", "--hide-scrollbars",
         "--allow-file-access-from-files", "--user-data-dir=" + prof,
         "--virtual-time-budget=4000", "--screenshot=" + out,
         "file://" + wp],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(14):
        time.sleep(2)
        if os.path.exists(out) and os.path.getsize(out) > 3000:
            return True
    return False


def main():
    for w, h in SIZES:
        wp = build(w, h)
        out = os.path.join(SHOT, "m_%dx%d.png" % (w, h))
        ok = shoot(wp, out, "%dx%d" % (w, h))
        print("%dx%d  %s" % (w, h, "ok" if ok else "FAIL"))
    print("完成")


if __name__ == "__main__":
    main()
