#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""重新生成节拍页副本（基于最新的 web/index.html）并加上测量脚本。"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
SRC = os.path.join(BASE, "web", "index.html")

html = io.open(SRC, encoding="utf-8").read()

# 切到节拍页
metro = html
metro = metro.replace("let currentPage = 'tuner';", "let currentPage = 'metro';", 1)
metro = metro.replace('<div class="page active" id="pageTuner">',
                      '<div class="page" id="pageTuner">', 1)
metro = metro.replace('<div class="page" id="pageMetro">',
                      '<div class="page active" id="pageMetro">', 1)
metro = metro.replace('<div class="app-tabs" id="appTabs"',
                      '<div class="app-tabs" id="appTabs" data-index="1"', 1)
metro = metro.replace('<button class="app-tab active" id="tabTuner"',
                      '<button class="app-tab" id="tabTuner"', 1)
metro = metro.replace('<button class="app-tab" id="tabMetro"',
                      '<button class="app-tab active" id="tabMetro"', 1)
metro = metro.replace("document.body.dataset.page = 'tuner';",
                      "document.body.dataset.page = 'metro';", 1)

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
  box('拍号',   '.meter-btn');
  box('圆环',   '.metro-ring');
  box('拍点',   '.beat-dots');
  box('音量条', '.vol-row');
  box('header', '.header');

  var d = document.createElement('div');
  d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
    'background:#000;color:#0f0;font:11px/1.45 monospace;padding:5px;white-space:pre';
  d.textContent = o.join('\\n');
  document.body.appendChild(d);
})();
</script>
"""

metro = metro.replace("</body>", MEASURE + "</body>", 1)
io.open(os.path.join(SHOT, "metro_m.html"), "w", encoding="utf-8").write(metro)

WRAP = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}
.c{width:390px;height:290px;overflow:hidden;position:relative}
iframe{width:390px;height:780px;border:0;display:block;position:absolute;left:0;top:0}
</style></head><body><div class="c"><iframe src="file://__S__"></iframe></div></body></html>"""
wp = os.path.join(SHOT, "mw3.html")
io.open(wp, "w", encoding="utf-8").write(
    WRAP.replace("__S__", os.path.join(SHOT, "metro_m.html")))
print("已生成", wp)
