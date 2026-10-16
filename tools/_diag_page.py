#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断用：把 web/index.html 复制一份，注入诊断脚本。

诊断脚本做的事：
  1. 显示视口尺寸 / 设备像素比
  2. 捕获 JS 运行时错误和 console.error
  3. 报告关键元素的实际尺寸与位置
  4. 检查页面是否横向/纵向溢出

输出到 .tmp_shot/diag.html，只用于本地截图检查。
"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "web", "index.html")
OUT = os.path.join(BASE, ".tmp_shot", "diag.html")

html = io.open(SRC, encoding="utf-8").read()

DIAG = """
<script>
(function(){
  var log = [];
  function add(s){ log.push(s); }

  window.addEventListener('error', function(e){
    add('ERR: ' + (e.message || '') + ' @' + (e.lineno || '?'));
  });
  var _ce = console.error;
  console.error = function(){
    add('CERR: ' + Array.prototype.slice.call(arguments).map(String).join(' ').slice(0,180));
    _ce.apply(console, arguments);
  };

  window.addEventListener('load', function(){
    setTimeout(function(){
      var de = document.documentElement;
      add('viewport ' + window.innerWidth + 'x' + window.innerHeight +
          ' dpr=' + window.devicePixelRatio);
      add('scroll ' + de.scrollWidth + 'x' + de.scrollHeight +
          ' overflowX=' + (de.scrollWidth > window.innerWidth) +
          ' overflowY=' + (de.scrollHeight > window.innerHeight));

      function box(sel){
        var n = document.querySelector(sel);
        if (!n) return sel + ' MISSING';
        var r = n.getBoundingClientRect();
        return sel + ' x=' + Math.round(r.left) + '..' + Math.round(r.right) +
               ' y=' + Math.round(r.top) + '..' + Math.round(r.bottom) +
               ' w=' + Math.round(r.width) + ' h=' + Math.round(r.height);
      }
      ['.app', '.header', '.app-tabs', '.header-right', '.brand',
       '.mode-tabs', '.center', '.gauge-block', '.target-area', '.strings',
       '.level-row', '.start', '.hint', '.meter-btn'].forEach(function(s){
        add(box(s));
      });

      var v = document.getElementById('volSeg');
      add('volSeg children=' + (v ? v.children.length : 'null'));
      var nw = document.getElementById('numWheel');
      add('numWheel children=' + (nw ? nw.children.length : 'null'));

      var pre = document.createElement('pre');
      pre.id = 'DIAGOUT';
      pre.style.cssText = 'position:fixed;left:0;top:0;z-index:99999;background:#000;' +
        'color:#0f0;font:11px/1.35 monospace;padding:6px;margin:0;max-width:100%;' +
        'white-space:pre-wrap;pointer-events:none';
      pre.textContent = log.join('\\n');
      document.body.appendChild(pre);
    }, 700);
  });
})();
</script>
"""

html = html.replace("</head>", DIAG + "</head>", 1)
io.open(OUT, "w", encoding="utf-8").write(html)
print("已生成", OUT, len(html), "字节")
