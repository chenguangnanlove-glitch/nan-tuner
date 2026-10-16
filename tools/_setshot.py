#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
生成"设置面板展开"的截图页：
  · 切到指定页面（tuner / metro）
  · 展开小太阳设置面板
  · 禁用过渡，保证截到的是展开终态

生成 phone_settings.html / phone_settings_metro.html，
用 _phoneshot.py 截图。
"""

import io
import os
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
SRC = os.path.join(BASE, "web", "index.html")

NOANIM = "<style>*,*::before,*::after{transition:none !important;animation:none !important}</style>"

INJECT = """
<script>
(function(){
  window.addEventListener('load', function(){
    setTimeout(function(){
      var tab = document.getElementById('%s');
      if (tab) tab.click();
      setTimeout(function(){
        var gear = document.getElementById('settingsBtn');
        var panel = document.getElementById('settingsPanel');
        if (!panel.classList.contains('open')) gear.click();
      }, 300);
    }, 300);
  });
})();
</script>
"""

WRAP = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;padding:0;background:#1a1a1a}
.phone{width:390px;height:780px;overflow:hidden;background:#000}
iframe{width:390px;height:780px;border:0;display:block;background:#000}
</style></head><body><div class="phone"><iframe src="file://__S__"></iframe></div></body></html>"""


def build(tab_id, tgt_name, wrap_name, label):
    html = io.open(SRC, encoding="utf-8").read()
    html = html.replace("</head>", NOANIM + "</head>", 1)
    html = html.replace("</body>", (INJECT % tab_id) + "</body>", 1)
    tgt = os.path.join(SHOT, tgt_name)
    io.open(tgt, "w", encoding="utf-8").write(html)
    wp = os.path.join(SHOT, wrap_name)
    io.open(wp, "w", encoding="utf-8").write(WRAP.replace("__S__", tgt))
    print("已生成", wp, "（%s）" % label)
    return wp


build("tabTuner", "settings_tuner.html", "phone_settings.html", "调音页")
build("tabMetro", "settings_metro.html", "phone_settings_metro.html", "节拍页")
