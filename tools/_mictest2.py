#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
在真实手机视口（390×780 iframe）里测试「开始调音」。

用 Chrome 的假麦克风设备，排除权限/硬件因素，
判断 start() 这段逻辑本身是否正常。

结果写在页面上（不依赖 setTimeout 也能看到的那部分）。
"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
SRC = os.path.join(BASE, "web", "index.html")

html = io.open(SRC, encoding="utf-8").read()

# 注入：把 alert / 错误 显示到页面顶部，并自动点击开始
INJECT = """
<script>
(function(){
  var log = [];
  function paint(){
    var el = document.getElementById('MJ');
    if (!el){
      el = document.createElement('div');
      el.id = 'MJ';
      el.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
        'background:#000;color:#0f0;font:12px/1.5 monospace;padding:6px;white-space:pre-wrap';
      document.body.appendChild(el);
    }
    el.textContent = log.join('\\n');
  }
  window.__log = log;
  window.__paint = paint;

  window.alert = function(m){ log.push('ALERT: ' + m); paint(); };
  window.addEventListener('error', function(e){
    log.push('ERR: ' + (e.message || '') + ' @' + (e.lineno || '?'));
    paint();
  });

  log.push('页面已载入');

  window.addEventListener('load', function(){
    setTimeout(function(){
      var b = document.getElementById('startBtn');
      if (!b){ log.push('startBtn NULL'); paint(); return; }
      log.push('按钮初始: ' + b.textContent.trim());
      paint();

      b.click();
      log.push('已点击 startBtn');
      paint();

      setTimeout(function(){
        log.push('点击后按钮: ' + b.textContent.trim());
        var mt = document.getElementById('micText');
        log.push('麦克风: ' + (mt ? mt.textContent : '?'));
        var ms = document.getElementById('micStatus');
        log.push('状态灯: ' + (ms ? (ms.classList.contains('on') ? '亮' : '灭') : '?'));
        var cs = document.getElementById('centsText');
        log.push('提示: ' + (cs ? cs.textContent : '?'));
        var ac = window.AudioContext || window.webkitAudioContext;
        log.push('AudioContext 可用: ' + !!ac);
        log.push('mediaDevices 可用: ' + !!(navigator.mediaDevices));
        paint();
      }, 3000);
    }, 600);
  });
})();
</script>
"""

html = html.replace("</body>", INJECT + "</body>", 1)
io.open(os.path.join(SHOT, "mictest2.html"), "w", encoding="utf-8").write(html)

WRAP = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  html,body{margin:0;padding:0;background:#1a1a1a}
  .phone{width:390px;height:780px;overflow:hidden;background:#000}
  iframe{width:390px;height:780px;border:0;display:block}
</style></head>
<body><div class="phone"><iframe src="__SRC__"></iframe></div></body></html>
"""
WRAP = WRAP.replace("__SRC__", "file://" + os.path.join(SHOT, "mictest2.html"))
io.open(os.path.join(SHOT, "phone_mic.html"), "w", encoding="utf-8").write(WRAP)

print("已生成 phone_mic.html")
