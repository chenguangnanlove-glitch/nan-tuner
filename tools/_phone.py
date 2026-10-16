#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
手机视口模拟器：用 iframe 精确构造 390×780 的视口。

为什么需要：这台机器的 Chrome 忽略 --window-size，视口恒为 500×813，
导致截图看到的排版不是手机上的样子。
iframe 内部是独立视口，媒体查询按 iframe 宽度计算 —— 这才是真机尺寸。

生成两个：
  phone_tuner.html  调音页
  phone_metro.html  节拍页（副本默认切到节拍）
"""

import io
import os
import re

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(BASE, "web", "index.html")
SHOT = os.path.join(BASE, ".tmp_shot")

html = io.open(SRC, encoding="utf-8").read()

# 节拍页副本：把默认页切成节拍，并把标签滑块也拨过去
metro = html.replace(
    'let currentPage = \'tuner\';',
    'let currentPage = \'metro\';', 1)
metro = metro.replace(
    '<div class="page active" id="pageTuner">',
    '<div class="page" id="pageTuner">', 1)
metro = metro.replace(
    '<div class="page" id="pageMetro">',
    '<div class="page active" id="pageMetro">', 1)
metro = metro.replace(
    '<div class="app-tabs" id="appTabs"',
    '<div class="app-tabs" id="appTabs" data-index="1"', 1)
metro = metro.replace(
    '<button class="app-tab active" id="tabTuner"',
    '<button class="app-tab" id="tabTuner"', 1)
metro = metro.replace(
    '<button class="app-tab" id="tabMetro"',
    '<button class="app-tab active" id="tabMetro"', 1)
metro = metro.replace(
    "document.body.dataset.page = 'tuner';",
    "document.body.dataset.page = 'metro';", 1)

io.open(os.path.join(SHOT, "metro_copy.html"), "w", encoding="utf-8").write(metro)

PAGE = """<!DOCTYPE html>
<html><head><meta charset="utf-8">
<style>
  html,body{margin:0;padding:0;background:#1a1a1a}
  .wrap{display:flex;gap:16px;padding:0}
  .phone{
    width:390px;height:780px;flex:none;overflow:hidden;
    background:#000;position:relative;
  }
  iframe{width:390px;height:780px;border:0;display:block;background:#000}
</style></head>
<body>
<div class="wrap"><div class="phone"><iframe src="__SRC__"></iframe></div></div>
</body></html>
"""

for name, src in (("phone_tuner.html", "file://" + SRC),
                  ("phone_metro.html", "file://" + os.path.join(SHOT, "metro_copy.html"))):
    out = PAGE.replace("__SRC__", src)
    io.open(os.path.join(SHOT, name), "w", encoding="utf-8").write(out)
    print("已生成", name)
