#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测量两页的实际高度，找出切换时的跳动量。

同时输出：
  · .app 高度（外层容器）
  · #pageTuner / #pageMetro 的 scrollHeight（内容真实高度）
  · 页面底部最后一个元素的位置
"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
SRC = os.path.join(BASE, "web", "index.html")

MEASURE = """
<script>
(function(){
  var o = [];
  var app = document.getElementById('app');
  var pt = document.getElementById('pageTuner');
  var pm = document.getElementById('pageMetro');

  o.push('app h=' + Math.round(app.getBoundingClientRect().height) +
         ' scrollH=' + app.scrollHeight);

  function info(lab, el){
    if (!el){ o.push(lab + ' MISSING'); return; }
    var r = el.getBoundingClientRect();
    o.push(lab + ' top=' + Math.round(r.top) + ' bottom=' + Math.round(r.bottom) +
           ' scrollH=' + el.scrollHeight + ' clientH=' + el.clientHeight);
  }
  info('pageTuner', pt);
  info('pageMetro', pm);

  // 调音页最后一个可见元素
  var last1 = document.querySelector('#pageTuner .hint');
  if (last1){ var r1 = last1.getBoundingClientRect();
    o.push('调音页尾部(hint) bottom=' + Math.round(r1.bottom)); }

  // 节拍页最后一个可见元素
  var last2 = document.querySelector('#pageMetro .vol-row');
  if (last2){ var r2 = last2.getBoundingClientRect();
    o.push('节拍页尾部(音量条) bottom=' + Math.round(r2.bottom)); }

  // 底部空余
  var appR = app.getBoundingClientRect();
  o.push('app 底边 y=' + Math.round(appR.bottom));

  var d = document.createElement('div');
  d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
    'background:#000;color:#0f0;font:11px/1.5 monospace;padding:6px;white-space:pre';
  d.textContent = o.join('\\n');
  document.body.appendChild(d);
})();
</script>
"""

html = io.open(SRC, encoding="utf-8").read()
html = html.replace("</body>", MEASURE + "</body>", 1)
tgt = os.path.join(SHOT, "hmeasure.html")
io.open(tgt, "w", encoding="utf-8").write(html)

WRAP = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}
.c{width:390px;height:300px;overflow:hidden;position:relative}
iframe{width:390px;height:780px;border:0;display:block;position:absolute;left:0;top:0}
</style></head><body><div class="c"><iframe src="file://__S__"></iframe></div></body></html>"""
wp = os.path.join(SHOT, "hmeasure_wrap.html")
io.open(wp, "w", encoding="utf-8").write(WRAP.replace("__S__", tgt))

print("已生成", wp)
