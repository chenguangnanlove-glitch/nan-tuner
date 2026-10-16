#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""测量钢琴黑白键的实际位置与宽度，核对是否符合真钢琴比例。"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
SRC = os.path.join(BASE, "web", "index.html")

html = io.open(SRC, encoding="utf-8").read()

INJECT = """
<script>
(function(){
  window.addEventListener('load', function(){
    setTimeout(function(){
      var t = document.querySelector('.mode-tab[data-mode="piano"]');
      if (t) t.click();

      setTimeout(function(){
        var o = [];
        var box = document.querySelector('.piano-keys');
        var br = box.getBoundingClientRect();
        o.push('键盘 left=' + Math.round(br.left) + ' right=' + Math.round(br.right) +
               ' w=' + Math.round(br.width) + ' h=' + Math.round(br.height));

        var whites = document.querySelectorAll('.pk-white .pkey');
        var w0 = whites[0].getBoundingClientRect();
        o.push('白键 数=' + whites.length + ' 宽=' + Math.round(w0.width) +
               ' 高=' + Math.round(w0.height));
        for (var i = 0; i < whites.length; i++){
          var r = whites[i].getBoundingClientRect();
          o.push('  #' + i + ' ' + whites[i].textContent + ' ' +
                 Math.round(r.left - br.left) + '-' + Math.round(r.right - br.left) +
                 ' w=' + Math.round(r.width));
        }

        var blacks = document.querySelectorAll('.pk-black .pkey');
        var b0 = blacks[0].getBoundingClientRect();
        o.push('黑键 数=' + blacks.length + ' 宽=' + Math.round(b0.width) +
               ' 高=' + Math.round(b0.height));
        for (var j = 0; j < blacks.length; j++){
          var r2 = blacks[j].getBoundingClientRect();
          var mid = (r2.left + r2.right) / 2 - br.left;
          o.push('  #' + j + ' ' + blacks[j].textContent + ' 中心=' + Math.round(mid) +
                 ' 宽=' + Math.round(r2.width));
        }

        o.push('对比：白键在 0-' + Math.round(br.width) + ' 之间均分');

        var d = document.createElement('div');
        d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
          'background:#000;color:#0f0;font:10px/1.4 monospace;padding:5px;white-space:pre';
        d.textContent = o.join('\\n');
        document.body.appendChild(d);
      }, 400);
    }, 300);
  });
})();
</script>
"""

html = html.replace("</body>", INJECT + "</body>", 1)
tgt = os.path.join(SHOT, "pianomeasure.html")
io.open(tgt, "w", encoding="utf-8").write(html)

WRAP = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}
.c{width:390px;height:300px;overflow:hidden;position:relative}
iframe{width:390px;height:780px;border:0;display:block;position:absolute;
       left:0;top:-430px}
</style></head><body><div class="c"><iframe src="file://__S__"></iframe></div></body></html>"""
wp = os.path.join(SHOT, "pianomeasure_wrap.html")
io.open(wp, "w", encoding="utf-8").write(WRAP.replace("__S__", tgt))

print("已生成", wp)
