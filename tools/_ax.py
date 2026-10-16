#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""两页锚点对照：调音页 vs 节拍页，在 780 / 844 两个视口高度下。

输出每页关键元素 top-bottom，并直接算出三条对齐轴的偏差：
  轴1 弧/环圆心 · 轴2 音量条/拍点 · 轴3 主按钮/节拍音量条
"""

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

  function mid(r){ return Math.round((r.top + r.bottom) / 2); }
  function line(sel, tag){
    var n = document.querySelector(sel);
    if (!n) { lines.push(tag + '  MISS'); return null; }
    var r = n.getBoundingClientRect();
    lines.push(tag + '  ' + Math.round(r.top) + '-' + Math.round(r.bottom) +
               '  中 ' + mid(r) + '  高 ' + Math.round(r.height));
    return r;
  }

  window.addEventListener('load', function(){
    setTimeout(function(){
      lines.push('viewport h=' + window.innerHeight);

      var tab = document.getElementById('tabMetro');
      if (tab) tab.click();
      setTimeout(function(){
        lines.push('— 节拍页 —');
        line('#pageMetro .metro-top', '拍号行');
        var ra = line('#pageMetro .metro-ring-area', '圆环区');
        line('#pageMetro .beat-dots', '拍点');
        line('#pageMetro .vol-row', '节拍音量条');
        var hm = line('#pageMetro .hint', '提示行');

        var tab2 = document.getElementById('tabTuner');
        if (tab2) tab2.click();
        setTimeout(function(){
          lines.push('— 调音页 —');
          var hd = line('#pageTuner .header', '页头');
          line('#pageTuner .target-area', '乐器行');
          line('#pageTuner .strings', '弦按钮');
          line('#pageTuner .level-row', '调音音量条');
          var st = line('#pageTuner .start', '主按钮');
          var pt = document.getElementById('pageTuner');
          var pr = pt.getBoundingClientRect();
          lines.push('调音页内容底 ' + Math.round(pr.bottom) + ' / 末尾元素底 ' +
                     (st ? Math.round(st.bottom) : '—'));
          lines.push('节拍页内容底 ' + Math.round(ra ? 0 : 0) + '');
          if (hm) lines.push('节拍页末尾元素底 ' + Math.round(hm.bottom));

          var d = document.createElement('div');
          d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
            'background:#000;color:#0f0;font:11px/1.45 monospace;padding:6px;white-space:pre';
          d.textContent = lines.join('\\n');
          document.body.appendChild(d);
        }, 500);
      }, 500);
    }, 400);
  });
})();
</script>
"""


def build(w, h, tag):
    html = io.open(SRC, encoding="utf-8").read()
    html = html.replace("</body>", MEASURE + "</body>", 1)
    tgt = os.path.join(SHOT, "ax_in_%s.html" % tag)
    io.open(tgt, "w", encoding="utf-8").write(html)
    wrap = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}
.c{width:%dpx;height:%dpx;overflow:hidden;position:relative}
iframe{width:%dpx;height:%dpx;border:0;display:block;position:absolute;left:0;top:0}
</style></head><body><div class="c"><iframe src="file://%s"></iframe></div></body></html>""" % (
        w, h, w, h, tgt)
    wp = os.path.join(SHOT, "ax_wrap_%s.html" % tag)
    io.open(wp, "w", encoding="utf-8").write(wrap)
    return wp


def shoot(wp, out, tag):
    if os.path.exists(out):
        os.remove(out)
    prof = os.path.join(SHOT, "_axp_" + tag)
    subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--disable-crash-reporter", "--no-first-run", "--hide-scrollbars",
         "--allow-file-access-from-files", "--user-data-dir=" + prof,
         "--virtual-time-budget=5000", "--screenshot=" + out,
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
    out = os.path.join(SHOT, "ax_%s.png" % tag)
    ok = shoot(wp, out, tag)
    print(tag, "ok" if ok else "FAIL")
print("完成")
