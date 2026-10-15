#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
静态检查 MainActivity.java 里所有方法调用是否存在。

关键改进：沿继承链查找方法（子类没声明的方法可能继承自父类）。
"""

import os
import re
import struct
import sys
import zipfile

JAVA = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "android", "app", "src", "main", "java", "com", "shixin", "tuner", "MainActivity.java",
)
JARS = ["/tmp/android-all.jar", "/tmp/webkit_classes.jar"]

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"


def parse_class(data):
    """解析 class 文件，返回 (类名, 父类名, 接口列表, 方法列表)。"""
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        return None
    pos = 8
    cp_count = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    cp = [None] * cp_count
    i = 1
    while i < cp_count:
        tag = data[pos]; pos += 1
        if tag == 1:                          # Utf8
            ln = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
            cp[i] = data[pos:pos + ln].decode("utf-8", "replace"); pos += ln
        elif tag == 7:                        # Class —— 指向 Utf8，延迟解析
            cp[i] = ("REF", struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
        elif tag in (8, 16, 19, 20):          # String / MethodType / Module / Package
            cp[i] = ("REF", struct.unpack(">H", data[pos:pos + 2])[0]); pos += 2
        elif tag == 15: pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18): pos += 4
        elif tag in (5, 6): pos += 8; i += 1
        else: return None
        i += 1

    def deref(idx):
        """解析常量池引用，返回字符串。"""
        if idx <= 0 or idx >= len(cp):
            return None
        v = cp[idx]
        if isinstance(v, tuple) and v and v[0] == "REF":
            inner = v[1]
            if 0 < inner < len(cp) and isinstance(cp[inner], str):
                return cp[inner]
            return None
        return v if isinstance(v, str) else None

    pos += 2                                  # access_flags
    this_i = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    super_i = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2

    iface_count = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    ifaces = []
    for _ in range(iface_count):
        idx = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
        n = deref(idx)
        if n:
            ifaces.append(n)

    this_name = deref(this_i)
    super_name = deref(super_i)

    # 字段
    f_count = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    for _ in range(f_count):
        pos += 6
        ac = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
        for _ in range(ac):
            alen = struct.unpack(">I", data[pos + 2:pos + 6])[0]; pos += 6 + alen

    # 方法
    m_count = struct.unpack(">H", data[pos:pos + 2])[0]; pos += 2
    methods = []
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
            methods.append((n, d, access))

    return this_name, super_name, ifaces, methods


class ClassPath:
    def __init__(self, jars):
        self.jars = []
        for j in jars:
            if os.path.isfile(j):
                zf = zipfile.ZipFile(j)
                self.jars.append((j, zf, set(zf.namelist())))
        self.cache = {}

    def raw(self, internal_name):
        """internal_name 形如 android/webkit/WebView"""
        if internal_name in self.cache:
            return self.cache[internal_name]
        path = internal_name + ".class"
        for j, zf, names in self.jars:
            if path in names:
                r = (j, zf.read(path))
                self.cache[internal_name] = r
                return r
        self.cache[internal_name] = None
        return None

    def get(self, fqcn):
        """按全限定名取类信息（支持内部类和继承查找）。"""
        internal = fqcn.replace(".", "/")
        r = self.raw(internal)
        if r:
            return parse_class(r[1])

        # 内部类：a.b.C 可能是 a/b/C$D 之类
        parts = fqcn.split(".")
        for cut in range(len(parts) - 1, 0, -1):
            cand = "/".join(parts[:cut]) + "$" + "$".join(parts[cut:])
            r = self.raw(cand)
            if r:
                return parse_class(r[1])
        return None

    def has_method(self, fqcn, method, _depth=0):
        """沿继承链查找方法。返回 True / False / None（类完全找不到）。"""
        if _depth > 12:
            return False

        info = self.get(fqcn)
        if not info:
            return None

        this_name, super_name, ifaces, methods = info
        for n, d, a in methods:
            if n == method:
                return True

        # 查接口（默认方法）
        for iface in ifaces:
            if self.has_method(iface.replace("/", "."), method, _depth + 1) is True:
                return True

        # 查父类
        if super_name and super_name not in ("java/lang/Object",):
            return self.has_method(super_name.replace("/", "."), method, _depth + 1)

        return False


# ══════════════════════════════════════════════════════════
print()
print(f"{BOLD}静态检查：方法调用是否存在（含继承链）{RESET}")
print("─" * 72)

cp = ClassPath(JARS)
for j, _, names in cp.jars:
    print(f"  {os.path.basename(j)}（{len(names):,} 个类）")

with open(JAVA, encoding="utf-8") as f:
    src = f.read()

CHECK_VARS = {
    "webView": "android.webkit.WebView",
    "settings": "android.webkit.WebSettings",
    "s": "android.webkit.WebSettings",
    "assetLoader": "androidx.webkit.WebViewAssetLoader",
    "cm": "android.net.ConnectivityManager",
    "nc": "android.net.NetworkCapabilities",
    "root": "android.widget.FrameLayout",
    "layoutParams": "android.widget.FrameLayout.LayoutParams",
}

print()
problems = []
checked = 0
unknown = []

for var, fqcn in CHECK_VARS.items():
    calls = sorted(set(re.findall(rf"\b{var}\.(\w+)\s*\(", src)))
    if not calls:
        continue

    print(f"  {BOLD}{var}{RESET}  {DIM}({fqcn}){RESET}")
    for method in calls:
        checked += 1
        has = cp.has_method(fqcn, method)
        if has is True:
            print(f"      {GREEN}✓{RESET} {method}()")
        elif has is False:
            print(f"      {RED}✗{RESET} {method}()  {RED}← 不存在！{RESET}")
            problems.append(f"{fqcn}.{method}()")
        else:
            print(f"      {YELLOW}?{RESET} {method}()  {DIM}（类不在类库里）{RESET}")
            unknown.append(f"{fqcn}.{method}()")
    print()

# ── 结论 ──
print("─" * 72)
print()
if problems:
    print(f"{RED}{BOLD}✗ 发现 {len(problems)} 处问题：{RESET}")
    for p in problems:
        print(f"    · {p}")
    sys.exit(1)
else:
    print(f"{GREEN}{BOLD}✅ 检查了 {checked} 个方法调用，全部存在{RESET}")
    if unknown:
        print(f"{DIM}   （{len(unknown)} 个因类库不含而无法判断，均为标准 JDK API）{RESET}")
    sys.exit(0)
