#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机宽度模拟页：强制 html/body 宽度 390，验证手机尺寸下的布局。

为什么这么做：这台机器上 Chrome 忽略 --window-size，视口恒为 500×813。
用 CSS 把宽度钉死 390，就能在 500 宽的视口里看到手机尺寸下的真实排版。
"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "web", "index.html")
OUT = os.path.join(BASE, ".tmp_shot", "w390sim.html")

html = io.open(SRC, encoding="utf-8").read()

FORCE = """
<style id="FORCEW">
  html, body {
    width: 390px !important;
    min-width: 390px !important;
    max-width: 390px !important;
    overflow-x: hidden !important;
  }
  body { justify-content: flex-start !important; }
  .app { max-width: 390px !important; }
</style>
"""

MEASURE = """
<script>
(function(){
  var o = [];
  var app = document.querySelector('.app');
  var ar = app.getBoundingClientRect();
  o.push('app w=' + Math.round(ar.width) + ' h=' + Math.round(ar.height));
  o.push('page scrollH=' + document.querySelector('#pageTuner').scrollHeight);

  ['.strings', '.mode-tabs', '.level-row', '.start', '.app-tabs'].forEach(function(s){
    var n = document.querySelector(s);
    if (!n) { o.push(s + ' MISS'); return; }
    var r = n.getBoundingClientRect();
    o.push(s + ' w=' + Math.round(r.width) + ' h=' + Math.round(r.height) +
           ' top=' + Math.round(r.top));
  });

  var d = document.createElement('div');
  d.style.cssText = 'position:fixed;left:0;top:0;width:390px;z-index:999999;' +
    'background:#000;color:#0f0;font:12px/1.4 monospace;padding:5px;white-space:pre';
  d.textContent = o.join('\\n');
  document.body.appendChild(d);
})();
</script>
"""

html = html.replace("</head>", FORCE + "</head>", 1)
html = html.replace("</body>", MEASURE + "</body>", 1)

io.open(OUT, "w", encoding="utf-8").write(html)
print("已生成", OUT)
