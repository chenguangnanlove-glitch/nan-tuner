#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""比对 web/index.html 与离线版是否逐字节一致（去掉 appRow 后）。"""

import io
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
W = io.open(os.path.join(BASE, "web", "index.html"), encoding="utf-8").read()
O = io.open(os.path.join(BASE, "android/app/src/main/assets/offline.html"),
            encoding="utf-8").read()

pat = re.compile(r'\n[ \t]*<div class="setting-row" id="appRow">.*?</div>[ \t]*\n', re.S)
Ws = pat.sub("\n", W)

print("网页版 %d 字符" % len(W))
print("离线版 %d 字符" % len(O))
print("去入口后 %d 字符" % len(Ws))
print("一致:", Ws == O)

if Ws != O:
    n = min(len(Ws), len(O))
    for i in range(n):
        if Ws[i] != O[i]:
            print("首个差异 @%d" % i)
            print("  web:", repr(Ws[max(0, i - 90):i + 90]))
            print("  off:", repr(O[max(0, i - 90):i + 90]))
            break
    else:
        print("前缀相同，仅长度不同")
