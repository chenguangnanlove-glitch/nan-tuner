#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
离线结构校验：不联网、不起服务，直接解析 HTML / JSON / XML，
确认生成的文件结构完整、标签配对、引用的资源都存在。

用法：  python3 tools/validate.py
"""

import html.parser
import json
import os
import re
import sys
import xml.etree.ElementTree as ET

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

VOID = {
    "area", "base", "br", "col", "embed", "hr", "img", "input",
    "link", "meta", "param", "source", "track", "wbr",
}

errors = []
notes = []


def err(m):
    errors.append(m)


def note(m):
    notes.append(m)


# ══════════════════════════════════════════════════════════════
#  1. HTML 标签配对检查
# ══════════════════════════════════════════════════════════════

class Checker(html.parser.HTMLParser):
    def __init__(self, path):
        super().__init__(convert_charrefs=True)
        self.path = path
        self.stack = []
        self.bad = []
        self.ids = {}
        self.dupe_ids = []
        self.refs = []          # (attr, value) 需要检查的本地资源
        self.has_viewport = False
        self.title = None
        self._in_title = False

    def handle_starttag(self, tag, attrs):
        d = dict(attrs)

        if tag == "meta":
            if (d.get("name") or "").lower() == "viewport":
                self.has_viewport = True

        if tag == "title":
            self._in_title = True

        _id = d.get("id")
        if _id:
            if _id in self.ids:
                self.dupe_ids.append(_id)
            self.ids[_id] = self.getpos()[0]

        for a in ("src", "href"):
            v = d.get(a)
            if v and not v.startswith(("http://", "https://", "//", "#", "data:", "mailto:", "javascript:")):
                self.refs.append((a, v))

        if tag not in VOID:
            self.stack.append((tag, self.getpos()[0]))

    def handle_startendtag(self, tag, attrs):
        d = dict(attrs)
        if tag == "meta" and (d.get("name") or "").lower() == "viewport":
            self.has_viewport = True
        _id = d.get("id")
        if _id:
            if _id in self.ids:
                self.dupe_ids.append(_id)
            self.ids[_id] = self.getpos()[0]
        for a in ("src", "href"):
            v = d.get(a)
            if v and not v.startswith(("http://", "https://", "//", "#", "data:", "mailto:", "javascript:")):
                self.refs.append((a, v))

    def handle_endtag(self, tag):
        if tag == "title":
            self._in_title = False
        if tag in VOID:
            return
        if not self.stack:
            self.bad.append(f"第 {self.getpos()[0]} 行：多余的 </{tag}>")
            return
        if self.stack[-1][0] == tag:
            self.stack.pop()
        else:
            for i in range(len(self.stack) - 1, -1, -1):
                if self.stack[i][0] == tag:
                    unclosed = [t for t, _ in self.stack[i + 1:]]
                    self.bad.append(
                        f"第 {self.getpos()[0]} 行的 </{tag}> 之前有未闭合标签：{unclosed}"
                    )
                    self.stack = self.stack[:i]
                    return
            self.bad.append(f"第 {self.getpos()[0]} 行：</{tag}> 没有对应的开始标签")

    def handle_data(self, data):
        if self._in_title and data.strip():
            self.title = data.strip()


def check_html(rel, label):
    path = os.path.join(BASE, rel)
    if not os.path.isfile(path):
        err(f"{label}：文件不存在 {rel}")
        return None

    with open(path, encoding="utf-8") as f:
        text = f.read()

    c = Checker(path)
    c.feed(text)
    c.close()

    print(f"\n\033[1m{label}\033[0m  ({len(text):,} 字符)")
    print(f"  标题：{c.title}")

    if c.bad:
        for b in c.bad:
            err(f"{label} {b}")
        print(f"  ❌ 标签有问题：{len(c.bad)} 处")
    else:
        print("  ✅ 标签全部配对")

    if c.stack:
        leftovers = [f"{t}(第{l}行)" for t, l in c.stack]
        err(f"{label} 未闭合标签：{leftovers}")
        print(f"  ❌ 未闭合：{leftovers}")
    else:
        print("  ✅ 无未闭合标签")

    if c.dupe_ids:
        err(f"{label} 有重复 id：{set(c.dupe_ids)}")
        print(f"  ❌ 重复 id：{set(c.dupe_ids)}")
    else:
        print(f"  ✅ {len(c.ids)} 个 id 均唯一")

    if c.has_viewport:
        print("  ✅ 有 viewport（手机等比显示）")
    else:
        err(f"{label} 缺少 viewport meta")
        print("  ❌ 缺少 viewport")

    # 检查本地资源引用
    missing = []
    for attr, val in c.refs:
        if val.startswith("/"):
            target = os.path.join(BASE, "web", val.lstrip("/"))
            if val.endswith("/"):
                target = os.path.join(target, "index.html")
        else:
            target = os.path.join(os.path.dirname(path), val)
        if not os.path.exists(target):
            missing.append(f'{attr}="{val}"')
    if missing:
        for m in missing:
            note(f"{label} 引用的文件本地尚不存在：{m}（部署后才会存在则属正常）")
        print(f"  ⚠️  {len(missing)} 个引用待部署后确认")
    else:
        print("  ✅ 本地资源引用都能找到")

    # 核心功能留存检查
    core = {
        "音高检测": "detectPitch",
        "麦克风采集": "getUserMedia",
        "频闪视图": "strobeCanvas",
        "音名显示": "noteName",
        "指针显示": "needleDot",
        "吉他模式": 'data-mode="guitar"',
        "尤克里里模式": 'data-mode="ukulele"',
        "钢琴模式": 'data-mode="piano"',
        "标准音高调节": "a4Value",
        "参考音播放": "playReference",
    }
    gone = [k for k, v in core.items() if v not in text]
    if gone:
        err(f"{label} 缺少功能：{gone}")
        print(f"  ❌ 缺少功能：{gone}")
    else:
        print(f"  ✅ {len(core)} 项核心功能全部保留")

    return c, text


web_c, web_text = check_html("web/index.html", "站点版")
off_c, off_text = check_html("android/app/src/main/assets/offline.html", "离线版")

# ══════════════════════════════════════════════════════════════
#  2. 与原始文件比对（确认没有意外改动原逻辑）
# ══════════════════════════════════════════════════════════════

print("\n\033[1m与原始文件比对\033[0m")
src = os.path.join(os.path.dirname(BASE), "index tuner.html")
if os.path.isfile(src):
    with open(src, encoding="utf-8") as f:
        original = f.read()

    # 原文件的每一行都应该完整出现在生成文件里
    orig_lines = [l for l in original.splitlines() if l.strip()]
    for rel, text, label in [
        ("web/index.html", web_text, "站点版"),
        ("android/app/src/main/assets/offline.html", off_text, "离线版"),
    ]:
        lost = [l.strip() for l in orig_lines if l not in text]
        if lost:
            err(f"{label} 丢失了原始文件的 {len(lost)} 行内容")
            print(f"  ❌ {label} 丢失 {len(lost)} 行，例如：{lost[0][:60]}")
        else:
            print(f"  ✅ {label} 完整保留原始文件的全部 {len(orig_lines)} 行")

    # 只有新增，没有删改
    grew_web = len(web_text) - len(original)
    grew_off = len(off_text) - len(original)
    print(f"  ℹ️  站点版增加 {grew_web:+,} 字符；离线版增加 {grew_off:+,} 字符")
    if grew_web <= 0:
        err("站点版没有新增内容，插入可能失败")
else:
    note(f"找不到原始文件 {src}，跳过比对")

# ══════════════════════════════════════════════════════════════
#  3. 插入内容专项检查
# ══════════════════════════════════════════════════════════════

print("\n\033[1m插入内容检查\033[0m")

checks = [
    ("站点版", web_text, [
        ("PWA 清单引用", 'rel="manifest"'),
        ("下载入口", 'id="appRow"'),
        ("App 环境检测", "ShixinApp"),
        ("Service Worker 注册", "serviceWorker.register"),
        ("图标引用", "/icons/icon-192.png"),
    ], True),
    ("离线版", off_text, [
        ("PWA 清单引用", 'rel="manifest"'),
        ("App 环境检测", "ShixinApp"),
    ], False),
]

for label, text, items, want_download in checks:
    for desc, marker in items:
        if marker in text:
            print(f"  ✅ {label}：{desc}")
        else:
            err(f"{label} 缺少{desc}")
            print(f"  ❌ {label}：{desc}")

    has_row = 'id="appRow"' in text
    if want_download and not has_row:
        err(f"{label} 缺少下载入口")
    if not want_download and has_row:
        err(f"{label} 不应有下载入口")

# 插入位置合理性：PWA 标签必须在 </head> 之前
for label, text in [("站点版", web_text), ("离线版", off_text)]:
    hi = text.find('rel="manifest"')
    he = text.find("</head>")
    if hi >= 0 and he >= 0 and hi < he:
        print(f"  ✅ {label}：PWA 标签在 </head> 之前")
    elif hi >= 0:
        err(f"{label}：PWA 标签位置错误（在 </head> 之后）")

    # 脚本必须在 </body> 之前
    si = text.rfind("serviceWorker")
    bi = text.find("</body>")
    if si >= 0 and bi >= 0 and si < bi:
        print(f"  ✅ {label}：附加脚本在 </body> 之前")

# ══════════════════════════════════════════════════════════════
#  4. JSON 文件校验
# ══════════════════════════════════════════════════════════════

print("\n\033[1mJSON 文件\033[0m")
for rel, must in [
    ("web/manifest.webmanifest", ["name", "short_name", "start_url", "display", "icons", "theme_color"]),
    ("web/app-version.json", ["versionCode", "versionName", "apk"]),
]:
    path = os.path.join(BASE, rel)
    try:
        with open(path, encoding="utf-8") as f:
            data = json.load(f)
        missing = [k for k in must if k not in data]
        if missing:
            err(f"{rel} 缺少字段 {missing}")
            print(f"  ❌ {rel} 缺少 {missing}")
        else:
            print(f"  ✅ {rel}（{len(data)} 个字段，格式合法）")
    except json.JSONDecodeError as e:
        err(f"{rel} JSON 语法错误：{e}")
        print(f"  ❌ {rel} 语法错误：{e}")
    except FileNotFoundError:
        err(f"{rel} 不存在")
        print(f"  ❌ {rel} 不存在")

# ══════════════════════════════════════════════════════════════
#  5. XML 校验
# ══════════════════════════════════════════════════════════════

print("\n\033[1mXML 文件\033[0m")
xml_files = [
    "android/app/src/main/AndroidManifest.xml",
    "android/app/src/main/res/values/strings.xml",
    "android/app/src/main/res/values/colors.xml",
    "android/app/src/main/res/values/themes.xml",
    "android/app/src/main/res/drawable/ic_launcher_background.xml",
    "android/app/src/main/res/mipmap-anydpi-v26/ic_launcher.xml",
    "android/app/src/main/res/mipmap-anydpi-v26/ic_launcher_round.xml",
]
for rel in xml_files:
    path = os.path.join(BASE, rel)
    try:
        ET.parse(path)
        print(f"  ✅ {os.path.basename(rel)}")
    except ET.ParseError as e:
        err(f"{rel} XML 语法错误：{e}")
        print(f"  ❌ {os.path.basename(rel)}：{e}")
    except FileNotFoundError:
        err(f"{rel} 不存在")
        print(f"  ❌ {os.path.basename(rel)} 不存在")

# ══════════════════════════════════════════════════════════════
#  6. YAML 基本结构
# ══════════════════════════════════════════════════════════════

print("\n\033[1mYAML 文件\033[0m")
yml_path = os.path.join(BASE, ".github/workflows/build-apk.yml")
try:
    with open(yml_path, encoding="utf-8") as f:
        yml_lines = f.readlines()
    bad = []
    for i, line in enumerate(yml_lines, 1):
        if "\t" in line.split("#")[0]:
            bad.append(i)
    if bad:
        err(f"build-apk.yml 第 {bad} 行用了 Tab（YAML 必须用空格）")
        print(f"  ❌ 有 Tab 缩进：第 {bad} 行")
    else:
        print("  ✅ 无 Tab 缩进")
    if any(l.strip().startswith("name:") for l in yml_lines):
        print("  ✅ 有 name 字段")
    else:
        err("build-apk.yml 缺少 name")
except FileNotFoundError:
    err("build-apk.yml 不存在")

# ══════════════════════════════════════════════════════════════
#  7. 图标尺寸
# ══════════════════════════════════════════════════════════════

print("\n\033[1m图标\033[0m")
try:
    from PIL import Image

    expect = {
        "web/icons/icon-192.png": (192, 192),
        "web/icons/icon-512.png": (512, 512),
        "web/icons/icon-maskable-512.png": (512, 512),
        "web/icons/favicon.png": (64, 64),
    }
    for dens, px in [("mdpi", 48), ("hdpi", 72), ("xhdpi", 96), ("xxhdpi", 144), ("xxxhdpi", 192)]:
        expect[f"android/app/src/main/res/mipmap-{dens}/ic_launcher.png"] = (px, px)
    for dens, px in [("mdpi", 108), ("hdpi", 162), ("xhdpi", 216), ("xxhdpi", 324), ("xxxhdpi", 432)]:
        expect[f"android/app/src/main/res/mipmap-{dens}/ic_launcher_foreground.png"] = (px, px)

    for rel, want in expect.items():
        path = os.path.join(BASE, rel)
        try:
            with Image.open(path) as im:
                got = im.size
                if got != want:
                    err(f"{rel} 尺寸应为 {want}，实际 {got}")
                    print(f"  ❌ {os.path.basename(rel)} 尺寸 {got} ≠ {want}")
                elif im.mode != "RGBA":
                    note(f"{rel} 色彩模式 {im.mode}（RGBA 更佳）")
        except FileNotFoundError:
            err(f"图标不存在：{rel}")
            print(f"  ❌ 缺少 {os.path.basename(rel)}")
    print(f"  ✅ 已核对 {len(expect)} 个图标（尺寸不符会单独列出）")
except ImportError:
    note("未安装 Pillow，跳过图标尺寸核对")

# ══════════════════════════════════════════════════════════════
print("\n" + "═" * 62)
if errors:
    print(f"\033[31m❌ {len(errors)} 个错误\033[0m")
    for i, e in enumerate(errors, 1):
        print(f"   {i}. {e}")
else:
    print("\033[32m✅ 结构校验全部通过\033[0m")
if notes:
    print(f"\n\033[33mℹ️  {len(notes)} 条备注：\033[0m")
    for i, n in enumerate(notes, 1):
        print(f"   {i}. {n}")
print("═" * 62)

sys.exit(1 if errors else 0)
