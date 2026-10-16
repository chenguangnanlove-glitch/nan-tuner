#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
全面检查 MainActivity.java 用到的 AndroidX API 是否都存在。

比 verify_api.py 更彻底：检查所有用到的类和它们的关键方法。
"""

import io
import os
import re
import struct
import sys
import zipfile

JARS = {
    "webkit": "/tmp/webkit_classes.jar",
    "annotation": "/tmp/annotation.jar",
}
JAVA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "android", "app", "src", "main", "java", "com", "shixin", "tuner", "MainActivity.java",
)

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"


def parse_class_methods(data):
    """从 .class 字节里提取 (方法名, 描述符, 访问标志)。"""
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        return []
    pos = 8
    cp_count = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2
    cp = [None] * cp_count
    i = 1
    while i < cp_count:
        tag = data[pos]; pos += 1
        if tag == 1:
            ln = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
            cp[i] = data[pos:pos + ln].decode("utf-8", "replace"); pos += ln
        elif tag in (7, 8, 16, 19, 20): pos += 2
        elif tag == 15: pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18): pos += 4
        elif tag in (5, 6): pos += 8; i += 1
        else: return []
        i += 1
    pos += 6
    if_count = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2 + if_count * 2
    f_count = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    for _ in range(f_count):
        pos += 6
        ac = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
        for _ in range(ac):
            alen = struct.unpack(">I", data[pos + 2:pos + 6])[0]; pos += 6 + alen
    m_count = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    out = []
    for _ in range(m_count):
        access = struct.unpack(">H", data[pos:pos + 2])[0]
        name_i = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        desc_i = struct.unpack(">H", data[pos + 4:pos + 6])[0]
        pos += 6
        ac = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
        for _ in range(ac):
            alen = struct.unpack(">I", data[pos + 2:pos + 6])[0]; pos += 6 + alen
        n = cp[name_i] if name_i < len(cp) else None
        d = cp[desc_i] if desc_i < len(cp) else None
        if n and d:
            out.append((n, d, access))
    return out


jar = zipfile.ZipFile(io.BytesIO(open(JARS["webkit"], "rb").read()))
names = set(jar.namelist())

# androidx.annotation 在单独的库里，一并加载
_ann = None
ann_names = set()
try:
    _ann = zipfile.ZipFile(JARS["annotation"])
    ann_names = set(_ann.namelist())
except Exception:
    pass

ALL_NAMES = names | ann_names

problems = []

with open(JAVA_FILE, encoding="utf-8") as f:
    java = f.read()

print()
print(f"{BOLD}检查 AndroidX API 使用{RESET}")
print("─" * 70)

# ── 1. 检查 AndroidX 的 import ──
print()
print(f"{BOLD}1. AndroidX 类的存在性{RESET}")
print()

androidx_imports = re.findall(r"^import\s+(androidx\.[\w.]+);", java, re.M)

for imp in androidx_imports:
    path = imp.replace(".", "/") + ".class"
    found = path in ALL_NAMES
    if not found:
        parent = imp.rsplit(".", 1)[0].replace(".", "/")
        inner = imp.rsplit(".", 1)[1]
        found = f"{parent}${inner}.class" in ALL_NAMES

    if found:
        where = "annotation 库" if path in ann_names else "webkit 库"
        print(f"  {GREEN}✓{RESET} {imp}  {DIM}（{where}）{RESET}")
    else:
        print(f"  {RED}✗{RESET} {imp}  {DIM}（两个库里都找不到）{RESET}")
        problems.append(imp)

# ── 2. 检查用到的具体方法 ──
print()
print(f"{BOLD}2. 关键方法调用{RESET}")
print()


def class_methods(fqcn):
    p = fqcn.replace(".", "/") + ".class"
    if p not in ALL_NAMES:
        # 试内部类
        parts = fqcn.split(".")
        for cut in range(len(parts) - 1, 0, -1):
            outer = "/".join(parts[:cut])
            inner = "$".join(parts[cut:])
            cand = f"{outer}${inner}.class"
            if cand in ALL_NAMES:
                p = cand
                break
        else:
            return None
    if p in ann_names:
        return parse_class_methods(_ann.read(p))
    return parse_class_methods(jar.read(p))


CHECKS = [
    ("androidx.webkit.WebViewAssetLoader", ["shouldInterceptRequest"]),
    ("androidx.webkit.WebViewAssetLoader$Builder", ["addPathHandler", "build"]),
    ("androidx.webkit.WebViewAssetLoader$AssetsPathHandler", ["<init>", "handle"]),
    ("androidx.webkit.WebViewClientCompat", ["shouldInterceptRequest",
                                              "shouldOverrideUrlLoading",
                                              "onReceivedError"]),
    ("androidx.webkit.WebResourceErrorCompat", []),
]

problems = []
for fqcn, methods in CHECKS:
    ms = class_methods(fqcn)
    if ms is None:
        print(f"  {RED}✗{RESET} 类不存在：{fqcn}")
        problems.append(fqcn)
        continue

    print(f"  {GREEN}✓{RESET} {fqcn}")
    for m in methods:
        hit = any(n == m for n, _, _ in ms)
        if hit:
            print(f"      {GREEN}✓{RESET} {m}()")
        else:
            # 可能是继承自父类。WebViewClientCompat 继承 android.webkit.WebViewClient，
            # 那里有 shouldInterceptRequest 等标准方法，覆盖它们是合法的。
            inherited = {
                "shouldInterceptRequest": "android.webkit.WebViewClient",
            }.get(m)
            if inherited:
                print(f"      {GREEN}✓{RESET} {m}()  {DIM}（继承自 {inherited.split('.')[-1]}，合法）{RESET}")
            else:
                print(f"      {RED}✗{RESET} {m}() 不存在")
                problems.append(f"{fqcn}.{m}")

# ── 3. 构建器链的调用方式 ──
print()
print(f"{BOLD}3. 代码里的调用链{RESET}")
print()

calls = re.findall(r"new\s+WebViewAssetLoader\.Builder\(\)[\s\S]{0,120}?\.build\(\)", java)
if calls:
    print(f"  {GREEN}✓{RESET} WebViewAssetLoader.Builder().…build() 调用链完整")
else:
    print(f"  {YELLOW}!{RESET} 没找到标准的 Builder 调用链")

if "new WebViewAssetLoader.AssetsPathHandler(this)" in java:
    print(f"  {GREEN}✓{RESET} AssetsPathHandler 的构造用法正确（接收 Context）")
else:
    print(f"  {YELLOW}!{RESET} AssetsPathHandler 用法需确认")

# ── 4. 确认没有遗留的错误类型 ──
print()
print(f"{BOLD}4. 残留检查{RESET}")
print()

if re.search(r"\bWebResourceError\b(?!Compat)", java):
    print(f"  {RED}✗{RESET} 还有 WebResourceError（应为 WebResourceErrorCompat）")
    for m in re.finditer(r".*\bWebResourceError\b(?!Compat).*", java):
        print(f"      {m.group(0).strip()[:70]}")
    problems.append("WebResourceError 残留")
else:
    print(f"  {GREEN}✓{RESET} 没有残留的 android.webkit.WebResourceError")

if "import androidx.webkit.WebResourceErrorCompat;" in java:
    print(f"  {GREEN}✓{RESET} 已 import WebResourceErrorCompat")
else:
    print(f"  {RED}✗{RESET} 缺少 WebResourceErrorCompat 的 import")
    problems.append("缺 import")

# ── 结论 ──
print()
print("─" * 70)
if problems:
    print(f"{RED}{BOLD}发现 {len(problems)} 处问题：{RESET}")
    for p in problems:
        print(f"  · {p}")
    sys.exit(1)
else:
    print(f"{GREEN}{BOLD}✅ AndroidX API 使用全部正确{RESET}")
    sys.exit(0)
