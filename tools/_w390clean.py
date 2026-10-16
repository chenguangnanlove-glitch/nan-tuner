#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""生成干净的 390 宽渲染页（只强制宽度，不加诊断层）。"""

import io
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "web", "index.html")
OUT = os.path.join(BASE, ".tmp_shot", "w390clean.html")

html = io.open(SRC, encoding="utf-8").read()

FORCE = """
<style>
  html, body {
    width: 390px !important;
    min-width: 390px !important;
    max-width: 390px !important;
    overflow-x: hidden !important;
  }
  body { justify-content: flex-start !important; }
  .app { max-width: 390px !important; }
</style>
"""

html = html.replace("</head>", FORCE + "</head>", 1)
io.open(OUT, "w", encoding="utf-8").write(html)
print("已生成", OUT)
