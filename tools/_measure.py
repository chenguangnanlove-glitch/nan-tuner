#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
对账工具：在手机视口（390×780）里测出所有关键元素的真实坐标，
跟设计图纸的目标值逐条对比，列出偏差。

目标值来自最终确认的设计：
  乐器按钮 / 4-4 拍号      116 - 158
  圆弧圆心 = 圆环圆心       390
  弦按钮 / 钢琴琴键         524 - 580（中线 552）
  音量条 / 节拍拍点         624
  开始调音 / 节拍音量条      696
"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
SRC = os.path.join(BASE, "web", "index.html")

TARGETS = [
    ("乐器行/拍号", ".mode-tabs", 116, 158),
    ("弦按钮",      ".strings",   524, 580),
    ("音量条",      ".level-row", 624, 640),
    ("主按钮",      ".start",     672, 720),
]

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
  box('乐器行', '.mode-tabs');
  box('弦按钮', '.strings');
  box('音量条', '.level-row');
  box('主按钮', '.start');
  box('header', '.header');
  box('切换键', '.app-tabs');

  // 表盘圆弧的圆心：从 SVG 的 viewBox 换算
  var g = document.querySelector('.gauge-svg');
  if (g){
    var gr = g.getBoundingClientRect();
    // 表盘 viewBox 0 0 400 240，圆心 (200, 210)，半径 140
    var cx = gr.left + gr.width * (200 / 400);
    var cy = gr.top + gr.height * (210 / 240);
    o.push('弧圆心 y=' + Math.round(cy) + ' x=' + Math.round(cx));
  }

  var d = document.createElement('div');
  d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
    'background:#000;color:#0f0;font:11px/1.45 monospace;padding:5px;white-space:pre';
  d.textContent = o.join('\\n');
  document.body.appendChild(d);
})();
</script>
"""

html = io.open(SRC, encoding="utf-8").read()
html = html.replace("</body>", MEASURE + "</body>", 1)
tgt = os.path.join(SHOT, "measure.html")
io.open(tgt, "w", encoding="utf-8").write(html)

WRAP = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}
.c{width:390px;height:380px;overflow:hidden;position:relative}
iframe{width:390px;height:780px;border:0;display:block;position:absolute;left:0;top:0}
</style></head><body><div class="c"><iframe src="file://__SRC__"></iframe></div></body></html>"""
wrap = WRAP.replace("__SRC__", tgt)
wp = os.path.join(SHOT, "measure_wrap.html")
io.open(wp, "w", encoding="utf-8").write(wrap)

print("已生成", wp)
print("目标: " + " | ".join("%s %d-%d" % t[:4] for t in TARGETS))
