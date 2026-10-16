#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测量节拍页关键元素在手机视口下的真实坐标。"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")

MEASURE = """
<script>
(function(){
  var o = [];
  function box(lab, sel){
    var n = document.querySelector(sel);
    if (!n) { o.push(lab + ' MISSING'); return; }
    var r = n.getBoundingClientRect();
    o.push(lab + ' ' + Math.round(r.top) + '-' + Math.round(r.bottom) +
           ' (h=' + Math.round(r.height) + ')');
  }
  box('拍号', '.meter-btn');
  box('圆环', '.metro-ring');
  box('拍点', '.beat-dots');
  box('音量条', '.vol-row');
  box('header', '.header');
  box('切换键', '.app-tabs');

  var d = document.createElement('div');
  d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
    'background:#000;color:#0f0;font:11px/1.45 monospace;padding:5px;white-space:pre';
  d.textContent = o.join('\\n');
  document.body.appendChild(d);
})();
</script>
"""

src = os.path.join(SHOT, "metro_copy.html")
html = io.open(src, encoding="utf-8").read()
html = html.replace("</body>", MEASURE + "</body>", 1)
tgt = os.path.join(SHOT, "measure2.html")
io.open(tgt, "w", encoding="utf-8").write(html)

WRAP = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}
.c{width:390px;height:300px;overflow:hidden;position:relative}
iframe{width:390px;height:780px;border:0;display:block;position:absolute;left:0;top:0}
</style></head><body><div class="c"><iframe src="file://__S__"></iframe></div></body></html>"""
w = WRAP.replace("__S__", tgt)
wp = os.path.join(SHOT, "mw2.html")
io.open(wp, "w", encoding="utf-8").write(w)

print("已生成", wp)
