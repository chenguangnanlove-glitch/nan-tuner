#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""小太阳（设置面板）展开前后，两页内容总高的变化。"""

import io
import os
import subprocess
import time

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SHOT = os.path.join(BASE, ".tmp_shot")
SRC = os.path.join(BASE, "web", "index.html")
CHROME = "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome"

MEASURE_HEAD = """<style>*,*::before,*::after{transition:none !important;animation:none !important}</style>
"""

MEASURE = """
<script>
(function(){
  var lines = [];
  var VH = 0;

  function snap(label, pageId){
    var pg = document.getElementById(pageId);
    var r = pg.getBoundingClientRect();
    var sh = document.documentElement.scrollHeight;
    var start = pg.querySelector('.start');
    var sr = start ? start.getBoundingClientRect() : null;
    lines.push(label +
      '  page底=' + Math.round(r.bottom) +
      '  文档高=' + sh +
      '  溢出=' + (sh > VH + 1 ? 'YES(+' + (sh - VH) + ')' : 'no') +
      (sr ? '  主按钮中=' + Math.round((sr.top + sr.bottom) / 2) : ''));
  }

  function go(page, metro, cb){
    var t = document.getElementById(metro ? 'tabMetro' : 'tabTuner');
    if (t) t.click();
    setTimeout(function(){
      var panel = document.getElementById('settingsPanel');
      var gear  = document.getElementById('settingsBtn');
      if (panel.classList.contains('open')) gear.click();   // 先确保收起
      setTimeout(function(){
        snap(page + ' 设置收', metro ? 'pageMetro' : 'pageTuner');
        gear.click();                                        // 真实点击展开
        setTimeout(function(){
          var pr = panel.getBoundingClientRect();
          var cs = getComputedStyle(panel);
          var inner = panel.querySelector('.settings-inner');
          var ir = inner ? inner.getBoundingClientRect() : null;
          lines.push('    面板 ' + Math.round(pr.top) + '-' + Math.round(pr.bottom) +
                     ' 高=' + Math.round(pr.height) + ' 宽=' + Math.round(pr.width) +
                     ' pos=' + cs.position + ' maxH=' + cs.maxHeight +
                     ' scrollH=' + panel.scrollHeight);
          if (ir) lines.push('    inner 宽=' + Math.round(ir.width) +
                             ' 高=' + Math.round(ir.height));
          var rows = panel.querySelectorAll('.setting-row');
          var rdesc = [];
          for (var i = 0; i < rows.length; i++){
            var rr = rows[i].getBoundingClientRect();
            rdesc.push('行' + i + '=' + Math.round(rr.width) + 'x' + Math.round(rr.height));
          }
          lines.push('    ' + rdesc.join('  '));
          snap(page + ' 设置展', metro ? 'pageMetro' : 'pageTuner');
          gear.click();                                      // 收回去
          setTimeout(cb, 400);
        }, 400);
      }, 300);
    }, 450);
  }

  window.addEventListener('load', function(){
    setTimeout(function(){
      VH = window.innerHeight;
      lines.push('viewport h=' + VH);
      go('调音页', false, function(){
        go('节拍页', true, function(){
          var d = document.createElement('div');
          d.style.cssText = 'position:fixed;left:0;top:0;right:0;z-index:999999;' +
            'background:#000;color:#0f0;font:11px/1.5 monospace;padding:6px;white-space:pre';
          d.textContent = lines.join('\\n');
          document.body.appendChild(d);
        });
      });
    }, 350);
  });
})();
</script>
"""


def build(w, h, tag):
    html = io.open(SRC, encoding="utf-8").read()
    html = html.replace("</head>", MEASURE_HEAD + "</head>", 1)
    html = html.replace("</body>", MEASURE + "</body>", 1)
    tgt = os.path.join(SHOT, "set_in_%s.html" % tag)
    io.open(tgt, "w", encoding="utf-8").write(html)
    wrap = """<!DOCTYPE html><html><head><meta charset="utf-8">
<style>html,body{margin:0;background:#000;overflow:hidden}
.c{width:%dpx;height:%dpx;overflow:hidden;position:relative}
iframe{width:%dpx;height:%dpx;border:0;display:block;position:absolute;left:0;top:0}
</style></head><body><div class="c"><iframe src="file://%s"></iframe></div></body></html>""" % (
        w, h, w, h, tgt)
    wp = os.path.join(SHOT, "set_wrap_%s.html" % tag)
    io.open(wp, "w", encoding="utf-8").write(wrap)
    return wp


def shoot(wp, out, tag):
    if os.path.exists(out):
        os.remove(out)
    prof = os.path.join(SHOT, "_setp_" + tag)
    subprocess.Popen(
        [CHROME, "--headless=new", "--disable-gpu", "--no-sandbox",
         "--disable-crash-reporter", "--no-first-run", "--hide-scrollbars",
         "--allow-file-access-from-files", "--user-data-dir=" + prof,
         "--virtual-time-budget=12000", "--screenshot=" + out,
         "file://" + wp],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    for _ in range(16):
        time.sleep(2)
        if os.path.exists(out) and os.path.getsize(out) > 3000:
            return True
    return False


for w, h in [(390, 780), (360, 640)]:
    tag = "%dx%d" % (w, h)
    wp = build(w, h, tag)
    out = os.path.join(SHOT, "set_%s.png" % tag)
    print(tag, "ok" if shoot(wp, out, tag) else "FAIL")
print("完成")
