#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
两页高度对比测量。

做法：先量调音页，再切到节拍页量一次，把两组数据都写进浮层。
"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
SRC = os.path.join(BASE, "web", "index.html")

MEASURE = """
<script>
(function(){
  var lines = [];

  function snap(label){
    var pt = document.getElementById('pageTuner');
    var pm = document.getElementById('pageMetro');
    var active = document.body.dataset.page === 'metro' ? pm : pt;
    var last = active.querySelector('.hint');
    var r = active.getBoundingClientRect();
    var lr = last ? last.getBoundingClientRect() : null;
    lines.push(label +
      '  内容 ' + Math.round(r.top) + '-' + Math.round(r.bottom) +
      '  高 ' + Math.round(r.height) +
      '  末尾元素底 ' + (lr ? Math.round(lr.bottom) : '—'));
  }

  function show(){
    var d = document.createElement('div');
    d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
      'background:#000;color:#0f0;font:12px/1.6 monospace;padding:8px;white-space:pre';
    d.textContent = lines.join('\\n');
    document.body.appendChild(d);
  }

  window.addEventListener('load', function(){
    setTimeout(function(){
      snap('调音页');
      var tab = document.getElementById('tabMetro');
      if (tab) tab.click();
      setTimeout(function(){
        snap('节拍页');
        show();
      }, 500);
    }, 400);
  });
})();
</script>
"""

html = io.open(SRC, encoding="utf-8").read()
html = html.replace("</body>", MEASURE + "</body>", 1)
tgt = os.path.join(SHOT, "h2.html")
io.open(tgt, "w", encoding="utf-8").write(html)

WRAP = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}
.c{width:390px;height:220px;overflow:hidden;position:relative}
iframe{width:390px;height:780px;border:0;display:block;position:absolute;left:0;top:0}
</style></head><body><div class="c"><iframe src="file://__S__"></iframe></div></body></html>"""
wp = os.path.join(SHOT, "h2_wrap.html")
io.open(wp, "w", encoding="utf-8").write(WRAP.replace("__S__", tgt))

print("已生成", wp)
