#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断页 v2：把测量结果写进 <title>，用 chrome --dump-dom 读取。

为什么这样：--screenshot 的时机在页面脚本执行完之前，
浮层来不及出现。写进 title 则是同步的，dump-dom 一定能读到。
"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "web", "index.html")
OUT = os.path.join(BASE, ".tmp_shot", "diag2.html")

html = io.open(SRC, encoding="utf-8").read()

# 1) 错误捕获：必须放在最前，才能抓到后面脚本的错
ERR_CATCH = """
<script>
window.__errs = [];
window.addEventListener('error', function(e){
  window.__errs.push('E:' + (e.message||'') + '@' + (e.lineno||'?'));
});
var _ce = console.error;
console.error = function(){
  window.__errs.push('C:' + Array.prototype.slice.call(arguments).map(String).join(' ').slice(0,150));
  _ce.apply(console, arguments);
};
</script>
"""

# 2) 测量：放在 </body> 前，此时 DOM 已解析完，同步执行
MEASURE = """
<script>
(function(){
  var o = [];
  var de = document.documentElement;
  o.push('VP=' + window.innerWidth + 'x' + window.innerHeight + ' dpr=' + window.devicePixelRatio);
  o.push('DOC=' + de.scrollWidth + 'x' + de.scrollHeight);

  function b(sel){
    var n = document.querySelector(sel);
    if (!n) return sel + '=MISS';
    var r = n.getBoundingClientRect();
    return sel + '=' + Math.round(r.left) + ',' + Math.round(r.top) + ',' +
           Math.round(r.width) + 'x' + Math.round(r.height);
  }
  ['.app','.header','.app-tabs','.header-right','.brand','.mode-tabs',
   '.center','.gauge-block','.target-area','.strings','.level-row','.start',
   '.hint','.meter-btn','.app-tab'].forEach(function(s){ o.push(b(s)); });

  var v = document.getElementById('volSeg');
  o.push('volSeg=' + (v ? v.children.length + 'kids' : 'NULL'));
  var nw = document.getElementById('numWheel');
  o.push('numWheel=' + (nw ? nw.children.length + 'kids' : 'NULL'));
  var sb = document.getElementById('startBtn');
  o.push('startBtn=' + (sb ? 'found' : 'NULL'));

  o.push('ERRS=' + window.__errs.length + '[' + window.__errs.slice(0,4).join(' | ') + ']');

  document.title = 'DIAG||' + o.join('||');
})();
</script>
"""

html = html.replace("<head>", "<head>" + ERR_CATCH, 1)
html = html.replace("</body>", MEASURE + "</body>", 1)

io.open(OUT, "w", encoding="utf-8").write(html)
print("已生成", OUT, len(html), "字节")
