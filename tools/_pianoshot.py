#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成"钢琴模式"的截图页：
  · 切到钢琴模式（buildPianoKeys 会跑起来）
  · 给一个假的音名和音分，让表盘有内容可看
  · 指针也拨到一个非零位置

生成 phone_piano.html，用 _phoneshot.py 截图。
"""

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
      // 1. 切到钢琴模式
      var t = document.querySelector('.mode-tab[data-mode="piano"]');
      if (t) t.click();

      // 2. 给表盘填个内容（模拟正在调音 A4，+2 音分）
      setTimeout(function(){
        var note = document.getElementById('noteName');
        if (note) note.innerHTML = '<span class="letter">A</span><span class="oct">4</span>';
        var cents = document.getElementById('centsText');
        if (cents){ cents.textContent = '+2 音分'; cents.className = 'cents ok'; }
        var freq = document.getElementById('freqText');
        if (freq) freq.textContent = '440.0 Hz';

        // 3. 让指针偏一点（+2 音分 = 3.6°）
        var dot = document.getElementById('needleDot');
        if (dot){
          var R = 172, CX = 200, CY = 208;
          var rad = 2 * 1.8 * Math.PI / 180;
          dot.setAttribute('cx', (CX + R * Math.sin(rad)).toFixed(2));
          dot.setAttribute('cy', (CY - R * Math.cos(rad)).toFixed(2));
        }

        // 4. 点亮 A4 那个键（第 5 个白键）
        var app = document.getElementById('app');
        if (app) app.classList.add('tuning-ok');
      }, 400);
    }, 300);
  });
})();
</script>
"""

html = html.replace("</body>", INJECT + "</body>", 1)
tgt = os.path.join(SHOT, "piano_mode.html")
io.open(tgt, "w", encoding="utf-8").write(html)

WRAP = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;padding:0;background:#1a1a1a}
.wrap{padding:0}.phone{width:390px;height:780px;overflow:hidden;background:#000}
iframe{width:390px;height:780px;border:0;display:block;background:#000}
</style></head><body><div class="phone"><iframe src="file://__S__"></iframe></div></body></html>"""
wp = os.path.join(SHOT, "phone_piano.html")
io.open(wp, "w", encoding="utf-8").write(WRAP.replace("__S__", tgt))

print("已生成", wp)
