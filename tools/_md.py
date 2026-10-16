#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""节拍页各元素在 780 与 844 两个高度下的位置对比。"""

import io
import os
import subprocess
import sys
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
SRC = os.path.join(BASE, "web", "index.html")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

MEASURE = """
<script>
(function(){
  var lines = [];
  window.addEventListener('load', function(){
    setTimeout(function(){
      var tab = document.getElementById('tabMetro');
      if (tab) tab.click();
      setTimeout(function(){
        lines.push('viewport h=' + window.innerHeight);
        var w = document.querySelector('.metro-wrap');
        var wr = w.getBoundingClientRect();
        lines.push('metro-wrap ' + Math.round(wr.top) + '-' + Math.round(wr.bottom) +
                   ' h=' + Math.round(wr.height));
        [' .metro-top', '.metro-ring-area', '.beat-dots', '.vol-row', '.hint'].forEach(function(s){
          var n = document.querySelector('#pageMetro ' + s.trim());
          if (!n) { lines.push(s + ' MISS'); return; }
          var r = n.getBoundingClientRect();
          lines.push(s.trim() + '  ' + Math.round(r.top) + '-' + Math.round(r.bottom) +
                     '  h=' + Math.round(r.height));
        });
        var d = document.createElement('div');
        d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
          'background:#000;color:#0f0;font:11px/1.5 monospace;padding:6px;white-space:pre';
        d.textContent = lines.join('\\n');
        document.body.appendChild(d);
      }, 400);
    }, 350);
  });
})();
</script>
"""


def build(w, h, tag):
    html = io.open(SRC, encoding="utf-8").read()
    html = html.replace("</body>", MEASURE + "</body>", 1)
    tgt = os.path.join(SHOT, "md_in_%s.html" % tag)
    io.open(tgt, "w", encoding="utf-8").write(html)
    wrap = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}
.c{width:%dpx;height:%dpx;overflow:hidden;position:relative}
iframe{width:%dpx;height:%dpx;border:0;display:block;position:absolute;left:0;top:0}
</style></head><body><div class="c"><iframe src="file://%s"></iframe></div></body></html>""" % (
        w, h, w, h, tgt)
    wp = os.path.join(SHOT, "md_wrap_%s.html" % tag)
    io.open(wp, "w", encoding="utf-8").write(wrap)
    return wp


def shoot(wp, out, tag):
    if os.path.exists(out):
        os.remove(out)
    prof = os.path.join(SHOT, "_dp_" + tag)
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


for w, h in [(390, 780), (390, 844)]:
    tag = "%dx%d" % (w, h)
    wp = build(w, h, tag)
    out = os.path.join(SHOT, "md_%s.png" % tag)
    ok = shoot(wp, out, tag)
    print(tag, "ok" if ok else "FAIL")
print("完成")
