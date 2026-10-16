#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把节拍器整合进 web/index.html。

本次改版要点（按用户反馈）：
  · 顶部切换改成胶囊滑块，朴素切换，不做缩放动效
  · 拍号改成下拉面板（分子 2-12 / 分母 2,4,6,8,12）
  · 圆环拖动调速，播放按钮放圆心
  · 圆环用渐变描边，观感更柔和

纯插入，不改动调音器原有的任何一行。
可重复运行（幂等）。
"""

import os
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, "web", "index.html")

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"

MARKER = "<!-- METRONOME-INTEGRATED -->"

text = open(WEB, encoding="utf-8").read()

# ── 幂等策略：替换而非「删了再插」──
#
# 之前用「删除 → 重新插入」，两边的空行结构不对称，
# 每跑一次就多几个空行（累积）。
#
# 现在改成：用正则匹配「标记之间的内容」直接替换。
# 标记外的空白完全不动，因此完全稳定。

HDR_S = "<!-- METRO-BLOCK:HEADER -->"
HDR_E = "<!-- /METRO-BLOCK:HEADER -->"
PAGE_S = "<!-- METRO-BLOCK:PAGES -->"
PAGE_E = "<!-- /METRO-BLOCK:PAGES -->"
CSS_S = "/* METRO-BLOCK:CSS */"
CSS_E = "/* /METRO-BLOCK:CSS */"
JS_S = "<!-- METRONOME-JS-INSERTED -->"

import re


def upsert(text, start_marker, end_marker, new_block, insert_before=None):
    """如果已存在这个块就替换，否则插到 insert_before 之前。

    new_block 可以带首尾空白（插入时用得上），
    但替换时**只取标记之间的部分** ——
    否则标记外的换行会被重复叠加，每跑一次就多一行空行。
    """
    # 只取核心部分
    i = new_block.find(start_marker)
    j = new_block.find(end_marker, i)
    core = new_block[i:j + len(end_marker)] if (i >= 0 and j >= 0) else new_block

    pattern = re.compile(
        re.escape(start_marker) + r".*?" + re.escape(end_marker),
        re.S)

    if pattern.search(text):
        return pattern.sub(lambda m: core, text, count=1)

    if insert_before is not None and insert_before in text:
        return text.replace(insert_before, insert_before + new_block, 1)

    return None


def strip_legacy(text):
    """清理最早那版（没有起止标记）留下的内容。"""
    # 旧的头部切换键
    text = re.sub(
        r"\n*\s*<!-- 调音 / 节拍 切换（由 tools/add_metronome\.py 插入） -->\s*\n"
        r'\s*<div class="app-tabs" id="appTabs"[^>]*>.*?\n\s*</div>\s*\n',
        "\n", text, flags=re.S)

    # 旧的节拍页
    text = re.sub(
        r"\n*\s*<!-- ═+\s*\n\s*节拍器页面（由 tools/add_metronome\.py 插入）\s*\n"
        r"\s*═+ -->.*?id=\"pageMetro\".*?\n\s*</div>\s*\n",
        "\n", text, flags=re.S)

    # 旧的拍号面板（可能单独残留）
    text = re.sub(
        r"\n*\s*<!-- 拍号选择面板 -->\s*\n"
        r'\s*<div class="meter-sheet" id="meterSheet">.*?\n\s*</div>\s*\n',
        "\n", text, flags=re.S)

    # 旧版的 pageTuner 包装（如果还残留）
    if 'id="pageMetro"' not in text:
        text = text.replace(
            '<div class="page active" id="pageTuner">\n\n  <div class="mode-tabs" id="modeTabs">',
            '<div class="mode-tabs" id="modeTabs">', 1)
        text = text.replace("\n\n  </div><!-- /pageTuner -->", "", 1)

    return text

problems = []

# ══════════════════════════════════════════════════════════
#  锚点检查（首次插入时才需要）
# ══════════════════════════════════════════════════════════

BRAND_END = """      <div class="brand-text">
        <div class="brand-cn">始信音乐</div>
        <div class="brand-en">SHIXIN MUSIC</div>
      </div>
    </div>"""

TABS_ANCHOR = '<div class="mode-tabs" id="modeTabs">'
HINT_LINE = '<div class="hint" id="hintText">'
STYLE_END = "</style>"

# 已经整合过 → 只做替换，不需要这些锚点
ALREADY = (HDR_S in text)

if not ALREADY:
    # 先清理更早那版（无标记）的残留，清理后可能就“已经是干净状态”了
    cleaned = strip_legacy(text)
    if cleaned != text:
        text = cleaned
        print(f"{DIM}已清理旧版残留{RESET}")

    for name, anchor in [
        ("品牌区块", BRAND_END),
        ("乐器切换", TABS_ANCHOR),
        ("提示文字", HINT_LINE),
        ("样式结尾", STYLE_END),
    ]:
        if anchor not in text:
            problems.append(f"找不到{name}")

    if problems:
        print(f"{RED}✗ 整合失败：{RESET}")
        for p in problems:
            print(f"    · {p}")
        sys.exit(1)

# ══════════════════════════════════════════════════════════
#  组装三块内容
# ══════════════════════════════════════════════════════════

HDR_BLOCK = f"""
{HDR_S}
    <!-- 调音 / 节拍 切换（由 tools/add_metronome.py 插入） -->
    <div class="app-tabs" id="appTabs" role="tablist">
      <span class="app-tabs-thumb" id="tabThumb"></span>
      <button class="app-tab active" id="tabTuner" type="button" role="tab">调音</button>
      <button class="app-tab" id="tabMetro" type="button" role="tab">节拍</button>
    </div>
    {HDR_E}"""

# ── 1. 头部切换键 ──
if ALREADY:
    text = upsert(text, HDR_S, HDR_E, HDR_BLOCK)
else:
    text = text.replace(BRAND_END, BRAND_END + HDR_BLOCK, 1)

# ══════════════════════════════════════════════════════════
#  2. CSS
# ══════════════════════════════════════════════════════════

CSS = """
  /* METRO-BLOCK:CSS */
  /* ══════════════════════════════════════════════════════
     节拍器样式（由 tools/add_metronome.py 插入）
     ══════════════════════════════════════════════════════ */

  /* ── 顶部切换键：胶囊滑块 ──
     朴素切换：只有背景位移和颜色变化，不做缩放/抖动 */
  .app-tabs{
    position:relative;flex:none;
    display:flex;
    background:var(--surface-2);
    border-radius:9px;
    padding:3px;
    margin-left:13px;
  }
  .app-tabs-thumb{
    position:absolute;
    top:3px;left:3px;
    width:calc(50% - 3px);
    height:calc(100% - 6px);
    border-radius:7px;
    background:var(--surface-3);
    transition:transform .22s cubic-bezier(.4,0,.2,1);
    pointer-events:none;
  }
  .app-tabs[data-index="1"] .app-tabs-thumb{
    transform:translateX(100%);
  }
  .app-tab{
    position:relative;z-index:1;
    appearance:none;border:0;background:transparent;
    color:var(--text-3);
    font-family:inherit;font-size:12px;font-weight:500;
    letter-spacing:.06em;
    padding:6px 14px;border-radius:7px;cursor:pointer;
    transition:color .2s;
    -webkit-tap-highlight-color:transparent;
    min-width:52px;
  }
  .app-tab.active{ color:var(--text) }

  /* 页面容器 */
  .page{display:none;flex-direction:column;flex:1;min-height:0}
  .page.active{display:flex}

  /* 切换页时的显示差异 */
  body[data-page="metro"] .mic{display:none}
  body[data-page="metro"] .setting-row:not(#appRow){display:none}

  /* ══════════════════════════════════════════════════════
     节拍器
     ══════════════════════════════════════════════════════ */
  .metro-wrap{
    display:flex;flex-direction:column;flex:1;
    min-height:0;
    /* 底部留白：让拍点落在 624、音量条落在 696（与调音页对齐） */
    padding-bottom:49px;
  }

  /* ── 顶部：拍号选择器（居中）── */
  .metro-top{
    display:flex;justify-content:center;
    flex:none;margin-bottom:0;
  }
  .meter-btn{
    appearance:none;border:1px solid var(--border-2);
    background:var(--surface-2);
    color:var(--text);
    font-family:inherit;font-size:14px;font-weight:500;
    letter-spacing:.04em;
    padding:12px 14px 12px 16px;border-radius:10px;
    cursor:pointer;
    display:flex;align-items:center;gap:7px;
    transition:background .18s, border-color .18s;
    -webkit-tap-highlight-color:transparent;
    font-variant-numeric:tabular-nums;
  }
  .meter-btn:active{ background:var(--surface-3) }
  .meter-btn .chev{
    width:9px;height:9px;flex:none;
    opacity:.55;
  }
  .meter-btn .chev path{
    stroke:currentColor;stroke-width:2;
    fill:none;stroke-linecap:round;stroke-linejoin:round;
  }

  /* ── 圆环调速区 ── */
  .metro-ring-area{
    --ring-max:310px;          /* 圆环直径上限（小屏断点会调低） */
    flex:1;
    display:flex;align-items:center;justify-content:center;
    min-height:0;
    position:relative;
    overflow:hidden;
    /* 让圆环圆心落在 390，与调音页的弧圆心对齐 */
    padding-top:25px;
  }
  /* 圆环尺寸由 JS（syncRingSize）按可用空间算出，写进 --ring-size。
     这里给「固定」宽高 —— 不能让尺寸由内容撑开，
     否则会形成「宽度→字号→数字宽度→宽度」的塌缩循环。 */
  .metro-ring{
    position:relative;
    width:var(--ring-size, 260px);
    height:var(--ring-size, 260px);
    flex:none;
    display:flex;align-items:center;justify-content:center;
    touch-action:none;          /* 拖动时不要触发页面滚动 */
    cursor:grab;
    -webkit-tap-highlight-color:transparent;
  }
  .metro-ring:active{ cursor:grabbing }
  .metro-ring svg{
    position:absolute;inset:0;width:100%;height:100%;
    overflow:visible;
  }

  /* 底圈：暗色轨道 */
  .ring-track{
    fill:none;
    stroke:var(--surface-3);
    stroke-width:2;
    stroke-linecap:round;
  }
  /* 进度弧：显示当前 BPM 在范围内的位置 */
  .ring-progress{
    fill:none;
    stroke:var(--accent);
    stroke-width:3;
    stroke-linecap:round;
    opacity:.5;
    transition:stroke-dashoffset .1s linear;
  }
  /* 脉冲环：每拍扩散 */
  .pulse-ring{
    fill:none;
    stroke:var(--accent);
    stroke-width:1.5;
    opacity:0;
    transform-box:fill-box;
    transform-origin:center;
  }
  .pulse-ring.beat{
    animation:metroPulse .44s cubic-bezier(.22,.61,.36,1);
  }
  @keyframes metroPulse{
    0%   { opacity:.7; transform:scale(.68) }
    100% { opacity:0;  transform:scale(1.02) }
  }

  /* ── 圆心：数字 + 术语 ──
     数字约占圆环直径的 1/3 */
  .ring-center{
    position:relative;z-index:1;
    display:flex;flex-direction:column;
    align-items:center;justify-content:center;
    width:80%;                  /* 限制在圆内 */
    pointer-events:none;        /* 空白处让拖动/点击穿透到圆环 */
  }

  /* 数字：占圆环直径的 1/3 以上，可点击输入。
     字号跟着圆环实际大小缩放 —— 这样“数字约占圆环 1/3”在任何屏幕上
     都成立。写死像素的话，小屏圆环被压小、字不变，就是“圈小字大”。
     内边距和圆角用 em，自动随字号等比缩放。 */
  .ring-bpm{
    pointer-events:auto;
    appearance:none;border:0;background:transparent;
    font-family:inherit;
    font-size:calc(var(--ring-size, 310px) * .339);
    font-weight:300;
    line-height:.92;
    color:var(--text);
    letter-spacing:-.03em;
    font-variant-numeric:tabular-nums;
    padding:.057em .152em;
    border-radius:.152em;
    cursor:text;
    transition:color .2s, background .16s;
    -webkit-tap-highlight-color:transparent;
  }
  .ring-bpm:active{ background:var(--surface-2) }
  .ring-bpm.hidden{ display:none }
  /* 播放中：数字变主色 */
  .ring-bpm.playing{ color:var(--accent) }

  /* 输入框：尺寸跟数字一致，避免跳动。
     宽度用 100%：自动跟随圆环大小，不会在大屏太宽、小屏溢出 */
  .ring-bpm-input{
    display:none;
    pointer-events:auto;
    font-family:inherit;
    font-size:calc(var(--ring-size, 310px) * .339);
    font-weight:300;
    line-height:.92;
    color:var(--accent);
    background:var(--surface-2);
    border:2px solid var(--accent);
    border-radius:.152em;
    width:100%;
    box-sizing:border-box;
    text-align:center;
    padding:.057em .038em;
    outline:none;
    letter-spacing:-.03em;
    font-variant-numeric:tabular-nums;
    -webkit-appearance:none;
  }
  .ring-bpm-input.show{ display:block }

  .ring-term{
    font-size:clamp(11px, calc(var(--ring-size, 310px) * .042), 14px);
    color:var(--text-3);
    letter-spacing:.08em;
    margin-top:calc(var(--ring-size, 310px) * .026);
    min-height:18px;
    transition:color .2s;
  }
  /* 播放中术语也跟着亮一点 */
  .ring-center.playing .ring-term{ color:var(--accent); opacity:.75 }

  /* ── 拍点指示 ──
     亮起的点带光晕：亮起瞬间点亮（.04s），熄灭时慢慢消退（.22s），
     形成「闪一下」的观感。光晕颜色跟随主题色（--accent-rgb）。 */
  .beat-dots{
    display:flex;justify-content:center;align-items:center;
    gap:16px;flex:none;
    height:30px;
    margin-top:4px;
  }
  .beat-dot{
    width:14px;height:14px;border-radius:50%;
    background:var(--surface-3);
    transition:background .22s ease-out, transform .22s ease-out,
               box-shadow .22s ease-out;
  }
  .beat-dot.accent{ width:16px;height:16px }
  .beat-dot.on{
    background:var(--success);
    transform:scale(1.25);
    box-shadow:0 0 7px 1px rgba(var(--success-rgb), .8),
               0 0 18px 5px rgba(var(--success-rgb), .3);
    transition:background .04s, transform .04s, box-shadow .04s;
  }
  /* 拍子多的时候（比如 12/8）缩小一点，避免挤成一片 */
  .beat-dots.dense{ gap:10px }
  .beat-dots.dense .beat-dot{ width:10px;height:10px }
  .beat-dots.dense .beat-dot.accent{ width:12px;height:12px }
  .beat-dots.dense .beat-dot.on{
    transform:scale(1.35);
    box-shadow:0 0 6px 1px rgba(var(--success-rgb), .75),
               0 0 14px 3px rgba(var(--success-rgb), .26);
  }

  /* ── 音量条：16 格分段刻度 ── */
  .vol-row{
    display:flex;align-items:center;justify-content:center;
    flex:none;
    width:min(84%, 312px);
    margin:46px auto 0;
    padding:0 2px;
  }
  .vol-seg{
    display:flex;align-items:center;gap:8px;
    width:100%;height:26px;
    cursor:pointer;touch-action:none;
    -webkit-tap-highlight-color:transparent;
  }
  .vol-seg i{
    flex:1 1 0;min-width:0;
    height:20px;border-radius:6px;
    background:var(--surface-3);
    transition:background .12s ease-out;
  }
  .vol-seg i.on{ background:var(--accent) }
  .vol-seg:focus-visible{ outline:2px solid var(--accent);outline-offset:4px }
  .vol-slider::-webkit-slider-runnable-track{
    height:3px;border-radius:2px;
    background:linear-gradient(to right,
      var(--accent) var(--vol-fill),
      var(--surface-3) var(--vol-fill));
  }
  .vol-slider::-webkit-slider-thumb{
    -webkit-appearance:none;
    width:14px;height:14px;border-radius:50%;
    background:var(--text);
    margin-top:-5.5px;           /* (3px 轨道 - 14px 滑块) / 2 */
    box-shadow:0 1px 4px rgba(0,0,0,.45);
  }
  .vol-slider::-moz-range-track{
    height:3px;border-radius:2px;background:var(--surface-3);
  }
  .vol-slider::-moz-range-progress{
    height:3px;border-radius:2px;background:var(--accent);
  }
  .vol-slider::-moz-range-thumb{
    width:14px;height:14px;border:0;border-radius:50%;
    background:var(--text);
    box-shadow:0 1px 4px rgba(0,0,0,.45);
  }

  /* ══════════════════════════════════════════════════════
     拍号选择：顶部下拉抽屉 + 双列滚轮
     分子 / 分母各一列，上下滑动选择，中间那条即选中。
     ══════════════════════════════════════════════════════ */
  .meter-sheet{
    position:fixed;inset:0;
    z-index:80;
    display:flex;align-items:flex-start;justify-content:center;
    background:rgba(0,0,0,.5);
    opacity:0;pointer-events:none;
    transition:opacity .22s;
  }
  .meter-sheet.open{
    opacity:1;pointer-events:auto;
  }
  .meter-sheet-body{
    width:100%;max-width:460px;
    background:var(--surface);
    border-bottom-left-radius:20px;
    border-bottom-right-radius:20px;
    padding:calc(16px + env(safe-area-inset-top)) 20px 20px;
    transform:translateY(-20px);
    transition:transform .24s cubic-bezier(.4,0,.2,1);
    border:1px solid var(--border-2);
    border-top:0;
  }
  .meter-sheet.open .meter-sheet-body{
    transform:translateY(0);
  }
  .meter-sheet-head{
    display:flex;align-items:center;justify-content:space-between;
    margin-bottom:6px;
  }
  .meter-sheet-title{
    font-size:14px;font-weight:500;color:var(--text);
    letter-spacing:.08em;
  }
  .meter-sheet-close{
    appearance:none;border:0;background:transparent;
    color:var(--accent);
    font-family:inherit;font-size:14px;font-weight:500;
    padding:6px 4px;cursor:pointer;
    letter-spacing:.04em;
    -webkit-tap-highlight-color:transparent;
  }

  /* ── 双列滚轮 ── */
  .meter-wheels{
    position:relative;
    display:flex;
    height:236px;              /* 5 行 × 46 + 留白 */
    margin-top:4px;
  }
  /* 中间的选中高亮条 */
  .meter-wheels::before{
    content:'';
    position:absolute;
    left:6px;right:6px;top:50%;
    height:52px;
    transform:translateY(-50%);
    border-radius:12px;
    background:var(--surface-2);
    border:1px solid var(--border-2);
    pointer-events:none;
  }
  .meter-wheel{
    position:relative;
    flex:1 1 0;min-width:0;
    height:100%;
    touch-action:none;
    cursor:grab;
    -webkit-tap-highlight-color:transparent;
    -webkit-mask-image:linear-gradient(to bottom,
      transparent, #000 26%, #000 74%, transparent);
            mask-image:linear-gradient(to bottom,
      transparent, #000 26%, #000 74%, transparent);
  }
  .meter-wheel:active{ cursor:grabbing }
  .meter-wheel-item{
    position:absolute;
    left:0;right:0;top:50%;
    height:46px;margin-top:-23px;
    display:flex;align-items:center;justify-content:center;
    font-size:18px;font-weight:500;
    font-variant-numeric:tabular-nums;
    color:var(--text-3);
    transition:color .16s, font-size .16s, opacity .16s;
    pointer-events:none;
  }
  .meter-wheel-item.near{ color:var(--text-2) }
  .meter-wheel-item.sel{ color:var(--text);font-size:25px }
  .meter-wheel-item.far{ opacity:.45 }

  /* ── 小屏适配 ──
     数字保持占圆环直径的 1/3 左右；
     极矮屏再压一级，避免内容和圆环挤在一起。 */
  @media (max-height: 780px){
    .metro-ring-area{ --ring-max:265px }
    .ring-term{ font-size:12px;margin-top:6px }
    .meter-btn{ font-size:13px;padding:7px 11px 7px 13px }
    .beat-dots{ height:23px;gap:7px }
    .beat-dot{ width:8.5px;height:8.5px }
    .beat-dot.accent{ width:11px;height:11px }
    .vol-row{ margin-top:46px }
  }
  @media (max-height: 660px){
    .metro-ring-area{ --ring-max:210px }
    .ring-term{ font-size:11px;margin-top:4px;min-height:15px }
    .ring-center{ width:74% }
    .vol-row{ margin-top:5px }
  }
  @media (max-height: 560px){
    .metro-ring-area{ --ring-max:160px }
    .ring-term{ font-size:10px;margin-top:3px;min-height:13px }
    .ring-center{ width:72% }
    .vol-row{ margin-top:4px }
  }
  /* 极矮屏（横屏、老设备）：一切从简 */
  @media (max-height: 430px){
    .metro-wrap{ gap:6px }
    .metro-top{ margin-bottom:3px }
    .meter-btn{ font-size:12px;padding:5px 9px 5px 11px }
    .metro-ring-area{ --ring-max:132px }
    .ring-term{ font-size:9px;margin-top:2px;min-height:12px }
    .ring-center{ width:70% }
    .beat-dots{ height:20px;gap:6px;margin-top:2px }
    .beat-dot{ width:7.5px;height:7.5px }
    .beat-dot.accent{ width:9px;height:9px }
    .vol-row{ margin-top:3px;gap:7px }
    .vol-icon{ width:15px;height:15px }
  }
  /* /METRO-BLOCK:CSS */
"""

if ALREADY:
    text = upsert(text, CSS_S, CSS_E, CSS)
else:
    text = text.replace(STYLE_END, CSS + STYLE_END, 1)

# ══════════════════════════════════════════════════════════
#  3. 节拍器页面 HTML
# ══════════════════════════════════════════════════════════

METRO_HTML = """
  <!-- METRO-BLOCK:PAGES -->
  <!-- ══════════════════════════════════════════════════════
       节拍器页面（由 tools/add_metronome.py 插入）
       ══════════════════════════════════════════════════════ -->
  <div class="page" id="pageMetro">
    <div class="metro-wrap">

      <!-- 拍号选择（右上） -->
      <div class="metro-top">
        <button class="meter-btn" id="meterBtn" type="button">
          <span id="meterLabel">4/4</span>
          <svg class="chev" viewBox="0 0 10 10" aria-hidden="true">
            <path d="M2 4 L5 7 L8 4"/>
          </svg>
        </button>
      </div>

      <!-- 圆环：拖动调速 -->
      <div class="metro-ring-area">
        <div class="metro-ring" id="metroRing">
          <svg viewBox="0 0 200 200" aria-hidden="true">
            <!-- 底圈 -->
            <circle class="ring-track" cx="100" cy="100" r="90"/>
            <!-- 速度进度弧 -->
            <circle class="ring-progress" id="ringProgress"
                    cx="100" cy="100" r="90"
                    transform="rotate(135 100 100)"/>
            <!-- 每拍脉冲 -->
            <circle class="pulse-ring" id="pulseRing"
                    cx="100" cy="100" r="90"/>
          </svg>

          <div class="ring-center" id="ringCenter">
            <button class="ring-bpm" id="bpmValue" type="button"
                    aria-label="点一下可输入速度">120</button>
            <input class="ring-bpm-input" id="bpmInput"
                   type="text" inputmode="numeric"
                   maxlength="3" autocomplete="off"
                   aria-label="输入速度">
            <div class="ring-term" id="bpmTerm">Moderato</div>
          </div>
        </div>
      </div>

      <!-- 拍点 -->
      <div class="beat-dots" id="beatDots"></div>

      <!-- 音量：16 格分段刻度 -->
      <div class="vol-row">
        <div class="vol-seg" id="volSeg" role="slider" tabindex="0"
             aria-label="节拍器音量"
             aria-valuemin="0" aria-valuemax="100" aria-valuenow="70"></div>
      </div>

    </div>
  </div>

  <!-- 拍号选择抽屉（顶部下拉 + 双列滚轮） -->
  <div class="meter-sheet" id="meterSheet">
    <div class="meter-sheet-body">
      <div class="meter-sheet-head">
        <span class="meter-sheet-title">拍号</span>
        <button class="meter-sheet-close" id="meterClose" type="button">完成</button>
      </div>
      <div class="meter-wheels">
        <div class="meter-wheel" id="numWheel" role="slider" tabindex="0"
             aria-label="拍号分子"></div>
        <div class="meter-wheel" id="denWheel" role="slider" tabindex="0"
             aria-label="拍号分母"></div>
      </div>
    </div>
  </div>
  <!-- /METRO-BLOCK:PAGES -->
"""

if ALREADY:
    text = upsert(text, PAGE_S, PAGE_E, METRO_HTML)
else:
    # 插到 .app 容器闭合之前
    hint_pos = text.find(HINT_LINE)
    close_pos = text.find("\n</div>", hint_pos)

    if close_pos < 0:
        print(f"{RED}✗ 找不到 .app 闭合位置{RESET}")
        sys.exit(1)

    text = text[:close_pos] + "\n" + METRO_HTML + text[close_pos:]

if not ALREADY and 'id="pageTuner"' not in text:
    tabs_pos = text.find(TABS_ANCHOR)
    if tabs_pos < 0:
        print(f"{RED}✗ 找不到乐器切换按钮{RESET}")
        sys.exit(1)

    text = (text[:tabs_pos]
            + '<div class="page active" id="pageTuner">\n\n  '
            + text[tabs_pos:])

    hint_pos2 = text.find(HINT_LINE)
    line_end = text.find("\n", hint_pos2)
    text = (text[:line_end]
            + "\n\n  </div><!-- /pageTuner -->"
            + text[line_end:])

# ══════════════════════════════════════════════════════════
#  写入
# ══════════════════════════════════════════════════════════

if text is None:
    print(f"{RED}✗ 块替换失败（找不到锚点）{RESET}")
    sys.exit(1)

shutil.copy2(WEB, WEB + ".pre-metro.bak")
with open(WEB, "w", encoding="utf-8") as f:
    f.write(text)

print(f"{GREEN}✓ 节拍器 HTML/CSS 已整合{RESET}")
print()
print(f"  {BOLD}本版改动：{RESET}")
print(f"    · 胶囊滑块切换键（朴素，无缩放动效）")
print(f"    · 拍号改下拉面板（分子 2-12 / 分母 2,4,6,8,12）")
print(f"    · 圆环拖动调速 + 圆心播放按钮")
print(f"    · 圆环加渐变进度弧")
print()
print(f"  {YELLOW}下一步：python3 tools/add_metronome_js.py{RESET}")
print()
