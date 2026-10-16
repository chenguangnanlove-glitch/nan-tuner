#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把 web/index.html 同步为 App 离线版 offline.html。

规则与 tools/build_web.py 的 generate_offline_only 一致：
  离线版 = 网页版 - 「手机 App 下载入口」那一行（appRow）

只做两件事：读取、去掉 appRow、写回离线版。不碰其它任何文件。
"""

import io
import os
import re
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, "web", "index.html")
OFF = os.path.join(BASE, "android", "app", "src", "main", "assets", "offline.html")

web = io.open(WEB, encoding="utf-8").read()

# 与 build_web.py 里 strip_app_row 完全相同的正则
pattern = re.compile(
    r'\n[ \t]*<div class="setting-row" id="appRow">.*?</div>[ \t]*\n',
    re.S,
)
off, n = pattern.subn("\n", web)

if n == 0:
    sys.exit("✗ 没找到 appRow 区块，中止（避免写入不完整内容）")

io.open(OFF, "w", encoding="utf-8").write(off)

print(f"✓ 已同步离线版")
print(f"  网页版 {len(web):>7,} 字符")
print(f"  离线版 {len(off):>7,} 字符（移除 {n} 处下载入口）")
