#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断页 v4：定位"谁把页面撑宽了"。

做法：遍历 .app 的所有后代，找出 getBoundingClientRect().right 超过
视口宽度的元素，以及自身 scrollWidth > clientWidth 的容器。
"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "web", "index.html")
OUT = os.path.join(BASE, ".tmp_shot", "diag4.html")

html = io.open(SRC, encoding="utf-8").read()

MEASURE = """
<script>
(function(){
  var o = [];
  var W = window.innerWidth;
  var de = document.documentElement;
  o.push('viewport ' + W + 'x' + window.innerHeight);
  o.push('doc scrollW ' + de.scrollWidth + '  (超出 ' + (de.scrollWidth - W) + ')');

  function tag(n){
    return n.tagName.toLowerCase() + (n.id ? '#' + n.id : '') +
           (n.className && typeof n.className === 'string' ? '.' + n.className.trim().split(/\\s+/)[0] : '');
  }

  // 1) 谁超出右边界
  o.push('--- 超出右边界的元素 ---');
  var all = document.querySelectorAll('.app *');
  var over = [];
  for (var i = 0; i < all.length; i++){
    var r = all[i].getBoundingClientRect();
    if (r.right > W + 0.5 && r.width > 0){
      over.push(tag(all[i]) + ' right=' + Math.round(r.right) + ' w=' + Math.round(r.width));
    }
  }
  o.push(over.length ? over.slice(0, 12).join('\\n') : '(无)');

  // 2) 谁的内容比自身宽
  o.push('--- 内部溢出的容器 ---');
  var inner = [];
  for (var j = 0; j < all.length; j++){
    var e = all[j];
    if (e.scrollWidth > e.clientWidth + 1 && e.clientWidth > 0){
      inner.push(tag(e) + ' client=' + e.clientWidth + ' scroll=' + e.scrollWidth);
    }
  }
  o.push(inner.length ? inner.slice(0, 12).join('\\n') : '(无)');

  // 3) .app 的宽度与各直接子元素宽度
  o.push('--- .app 直接子元素 ---');
  var app = document.querySelector('.app');
  var ar = app.getBoundingClientRect();
  o.push('.app w=' + Math.round(ar.width) + ' scrollW=' + app.scrollWidth);
  for (var k = 0; k < app.children.length; k++){
    var c = app.children[k];
    var cr = c.getBoundingClientRect();
    o.push('  ' + tag(c) + ' w=' + Math.round(cr.width) +
           ' scrollW=' + c.scrollWidth + ' scrollH=' + c.scrollHeight);
  }

  var d = document.createElement('div');
  d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
    'background:#000;color:#0f0;font:11px/1.4 monospace;padding:6px;' +
    'white-space:pre;overflow:hidden;max-height:100vh';
  d.textContent = o.join('\\n');
  document.body.appendChild(d);
})();
</script>
"""

html = html.replace("</body>", MEASURE + "</body>", 1)
io.open(OUT, "w", encoding="utf-8").write(html)
print("已生成", OUT)
