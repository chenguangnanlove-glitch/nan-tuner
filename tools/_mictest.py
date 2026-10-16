#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
麦克风自检页：自动点击「开始调音」，并把结果画在页面上。

用 Chrome 的假麦克风设备运行，用来判断 start() 这段逻辑本身
是否正常（排除权限、设备等外部因素）。
"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "web", "index.html")
OUT = os.path.join(BASE, ".tmp_shot", "mictest.html")

html = io.open(SRC, encoding="utf-8").read()

TEST = """
<script>
(function(){
  var out = [];
  // 把 alert 换成页面上的红条，否则 headless 下会卡住
  window.alert = function(m){
    out.push('ALERT: ' + m);
    render();
  };
  window.addEventListener('error', function(e){
    out.push('ERR: ' + (e.message || '') + ' @' + (e.lineno || '?'));
    render();
  });

  function render(){
    var el = document.getElementById('MICOUT');
    if (!el){
      el = document.createElement('div');
      el.id = 'MICOUT';
      el.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
        'background:#000;color:#0f0;font:12px/1.45 monospace;padding:6px;' +
        'white-space:pre-wrap';
      document.body.appendChild(el);
    }
    el.textContent = out.join('\\n');
  }

  render();

  window.addEventListener('load', function(){
    setTimeout(function(){
      var b = document.getElementById('startBtn');
      if (!b){ out.push('startBtn 找不到'); render(); return; }
      out.push('点击前: ' + b.textContent.trim());
      try { b.click(); } catch (e) { out.push('click 抛错: ' + e.message); }

      setTimeout(function(){
        out.push('点击后: ' + b.textContent.trim());
        var mt = document.getElementById('micText');
        out.push('麦克风状态: ' + (mt ? mt.textContent : '?'));
        var cs = document.getElementById('centsText');
        out.push('提示文字: ' + (cs ? cs.textContent : '?'));
        var ms = document.getElementById('micStatus');
        out.push('状态灯 on: ' + (ms ? ms.classList.contains('on') : '?'));
        render();
      }, 2500);
    }, 500);
  });
})();
</script>
"""

html = html.replace("</body>", TEST + "</body>", 1)
io.open(OUT, "w", encoding="utf-8").write(html)
print("已生成", OUT)
