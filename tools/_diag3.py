#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断页 v3：同步测量 + 把结果画在页面上（大字号），配合 --screenshot 读取。

要点：脚本放在 </body> 前同步执行，不依赖 setTimeout/load，
      截图一定能拍到。
"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "web", "index.html")
OUT = os.path.join(BASE, ".tmp_shot", "diag3.html")

html = io.open(SRC, encoding="utf-8").read()

ERR_CATCH = """
<script>
window.__errs = [];
window.addEventListener('error', function(e){
  window.__errs.push((e.message||'') + '@' + (e.lineno||'?'));
});
</script>
"""

MEASURE = """
<script>
(function(){
  var o = [];
  var de = document.documentElement;
  o.push('视口 ' + window.innerWidth + ' x ' + window.innerHeight + '  dpr ' + window.devicePixelRatio);
  o.push('文档 ' + de.scrollWidth + ' x ' + de.scrollHeight);

  var over = de.scrollWidth > window.innerWidth;
  o.push('横向溢出: ' + (over ? '是 !!!  超出 ' + (de.scrollWidth - window.innerWidth) + 'px' : '否'));

  function b(lab, sel){
    var n = document.querySelector(sel);
    if (!n) { o.push(lab + ' 缺失'); return; }
    var r = n.getBoundingClientRect();
    o.push(lab + '  left=' + Math.round(r.left) + '  right=' + Math.round(r.right) +
           '  w=' + Math.round(r.width) + '  h=' + Math.round(r.height));
  }
  b('header', '.header');
  b('切换键', '.app-tabs');
  b('右侧区', '.header-right');
  b('品牌区', '.brand');
  b('乐器行', '.mode-tabs');
  b('弦按钮', '.strings');
  b('音量条', '.level-row');
  b('主按钮', '.start');

  var v = document.getElementById('volSeg');
  o.push('音量格 ' + (v ? v.children.length + ' 个' : '缺失'));
  o.push('错误 ' + window.__errs.length + ' 个 ' + window.__errs.slice(0,2).join(' / '));

  var d = document.createElement('div');
  d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
    'background:#000;color:#0f0;font:13px/1.5 monospace;padding:8px;' +
    'white-space:pre;border-bottom:2px solid #0f0';
  d.textContent = o.join('\\n');
  document.body.appendChild(d);
})();
</script>
"""

html = html.replace("<head>", "<head>" + ERR_CATCH, 1)
html = html.replace("</body>", MEASURE + "</body>", 1)

io.open(OUT, "w", encoding="utf-8").write(html)
print("已生成", OUT, len(html), "字节")
