#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 MainActivity.java 里用到的 AndroidX API 签名是否正确。

做法：下载 androidx.webkit 的 AAR，解出 classes.jar，
再解析 .class 文件，提取 WebViewClientCompat 的真实方法签名。
然后和我们的代码逐一对照。

这样就不用靠「记忆」判断 API 对不对。
"""

import io
import os
import re
import struct
import sys
import urllib.request
import zipfile

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nethelper import ssl_context  # noqa: E402

AAR_URL = ("https://dl.google.com/dl/android/maven2/"
           "androidx/webkit/webkit/1.12.1/webkit-1.12.1.aar")

JAVA_FILE = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "android", "app", "src", "main", "java", "com", "shixin", "tuner", "MainActivity.java",
)

CACHE = "/tmp/webkit_classes.jar"

GREEN = "\033[32m"
RED = "\033[31m"
YELLOW = "\033[33m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def sep(t):
    print()
    print(f"\033[1m{t}\033[0m")
    print("─" * 70)


# ════════════════════════════════════════════════════════════
sep("1. 获取 androidx.webkit 库")

if os.path.isfile(CACHE):
    print(f"  使用缓存：{CACHE}")
    jar_bytes = open(CACHE, "rb").read()
else:
    print(f"  下载：{AAR_URL}")
    try:
        req = urllib.request.Request(AAR_URL, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=60, context=ssl_context()) as r:
            aar = r.read()
        print(f"  下载完成：{len(aar):,} 字节")

        zf = zipfile.ZipFile(io.BytesIO(aar))
        names = zf.namelist()
        print(f"  AAR 内含：{', '.join(n for n in names if n.endswith('.jar'))}")

        jar_bytes = zf.read("classes.jar")
        with open(CACHE, "wb") as f:
            f.write(jar_bytes)
        print(f"  解出 classes.jar：{len(jar_bytes):,} 字节")
    except Exception as e:
        print(f"  ✗ 下载失败：{type(e).__name__}: {e}")
        sys.exit(1)

jar = zipfile.ZipFile(io.BytesIO(jar_bytes))


# ════════════════════════════════════════════════════════════
#  极简 class 文件解析：只提取方法名和描述符
# ════════════════════════════════════════════════════════════

def parse_class_methods(data):
    """从 .class 字节里提取 (方法名, 描述符) 列表。"""
    if len(data) < 10 or data[:4] != b"\xca\xfe\xba\xbe":
        return []

    pos = 8
    cp_count = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2

    # 常量池
    cp = [None] * cp_count
    i = 1
    while i < cp_count:
        tag = data[pos]
        pos += 1
        if tag == 1:                      # Utf8
            ln = struct.unpack(">H", data[pos:pos + 2])[0]
            pos += 2
            cp[i] = data[pos:pos + ln].decode("utf-8", "replace")
            pos += ln
        elif tag in (7, 8, 16, 19, 20):   # 引用类/字符串/方法类型/模块/包
            pos += 2
        elif tag in (15,):                # MethodHandle
            pos += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            pos += 4
        elif tag in (5, 6):               # Long / Double 占两位
            pos += 8
            i += 1
        else:
            return []
        i += 1

    # 跳过访问标志、this、super
    pos += 6

    # 接口
    if_count = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2 + if_count * 2

    # 字段
    f_count = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2
    for _ in range(f_count):
        pos += 6
        ac = struct.unpack(">H", data[pos:pos + 2])[0]
        pos += 2
        for _ in range(ac):
            alen = struct.unpack(">I", data[pos + 2:pos + 6])[0]
            pos += 6 + alen

    # 方法
    m_count = struct.unpack(">H", data[pos:pos + 2])[0]
    pos += 2

    out = []
    for _ in range(m_count):
        access = struct.unpack(">H", data[pos:pos + 2])[0]
        name_i = struct.unpack(">H", data[pos + 2:pos + 4])[0]
        desc_i = struct.unpack(">H", data[pos + 4:pos + 6])[0]
        pos += 6
        ac = struct.unpack(">H", data[pos:pos + 2])[0]
        pos += 2
        for _ in range(ac):
            alen = struct.unpack(">I", data[pos + 2:pos + 6])[0]
            pos += 6 + alen

        name = cp[name_i] if name_i < len(cp) else None
        desc = cp[desc_i] if desc_i < len(cp) else None
        if name and desc:
            out.append((name, desc, access))
    return out


# ── 提取 WebViewClientCompat ──
TARGET = "androidx/webkit/WebViewClientCompat.class"
if TARGET not in jar.namelist():
    print(f"\n  ✗ jar 里找不到 {TARGET}")
    print(f"  可用内容（前 20 个）：")
    for n in jar.namelist()[:20]:
        print(f"    {n}")
    sys.exit(1)

data = jar.read(TARGET)
methods = parse_class_methods(data)

sep("2. WebViewClientCompat 的公开方法（真实签名）")

MOD = {"public": 0x0001, "protected": 0x0004, "private": 0x0002,
       "final": 0x0010, "abstract": 0x0400, "deprecated": 0x20000}

interesting = []
for name, desc, access in methods:
    if name.startswith("<"):
        continue
    if not (access & (MOD["public"] | MOD["protected"])):
        continue
    flags = []
    if access & MOD["final"]:
        flags.append("final")
    if access & MOD["abstract"]:
        flags.append("abstract")
    if access & MOD["deprecated"]:
        flags.append("deprecated")

    # 只显示和我们代码相关的
    if name in ("onReceivedError", "shouldInterceptRequest", "shouldOverrideUrlLoading",
                "onPageFinished", "onReceivedHttpError"):
        interesting.append((name, desc, flags))

for name, desc, flags in sorted(interesting):
    mark = " \033[31m← final！不能覆盖\033[0m" if "final" in flags else ""
    print(f"  {name}{desc}")
    if flags:
        print(f"      标志：{', '.join(flags)}{mark}")
    print()


# ════════════════════════════════════════════════════════════
sep("3. 对照我们的代码")

with open(JAVA_FILE, encoding="utf-8") as f:
    java = f.read()

def extract_param_type(param):
    """从 Java 参数声明里提取类型。

    'WebView view'            → 'WebView'
    '@NonNull WebResourceRequest request' → 'WebResourceRequest'
    'final int code'          → 'int'
    """
    p = re.sub(r"@\w+(?:\([^)]*\))?\s+", "", param.strip())  # 去注解
    p = re.sub(r"^final\s+", "", p)
    parts = p.split()
    if len(parts) >= 2:
        return parts[-2]
    return p


# 找出我们覆盖的方法
overrides = re.findall(
    r"public\s+([\w<>\[\].]+)\s+(\w+)\s*\(([^)]*)\)",
    java
)

print("  我们覆盖的方法：")
our_methods = {}
for ret, name, args in overrides:
    if name in ("onReceivedError", "shouldInterceptRequest", "shouldOverrideUrlLoading"):
        argtypes = [extract_param_type(a) for a in args.split(",") if a.strip()]
        our_methods[name] = argtypes
        print(f"    {name}({', '.join(argtypes)})")

print()
print("  与库对照：")
PROBLEMS = []

for name, our_args in our_methods.items():
    # 找库里同名方法
    candidates = [(d, fl) for (n, d, fl) in methods if n == name and not n.startswith("<")]

    if not candidates:
        print(f"    · {name}：WebViewClientCompat 里没有，应该是继承自父类")
        print(f"        {DIM}（这很正常，Java 允许覆盖继承的方法）{RESET}")
        continue

    matched = False
    for desc, flags in candidates:
        # 从描述符提取参数类型
        m = re.match(r"\((.*?)\)", desc)
        params = re.findall(r"L([\w/$]+);|\[?([ZBCSIJFD])", m.group(1)) if m else []
        lib_args = [p[0].split("/")[-1] if p[0] else p[1] for p in params]

        if lib_args == our_args or (
            len(lib_args) == len(our_args)
            and all(a == b or a.endswith(b) or b.endswith(a)
                    for a, b in zip(lib_args, our_args))
        ):
            if flags & MOD["final"]:
                print(f"    ✗ {name}：签名匹配，但库里是 final —— 无法覆盖！")
                PROBLEMS.append(name)
            else:
                print(f"    ✓ {name}：签名正确，且可覆盖")
            matched = True
            break

    if not matched:
        print(f"    ✗ {name}：签名不匹配")
        print(f"        我们的：{our_args}")
        for desc, flags in candidates:
            print(f"        库里的：{desc}")
        PROBLEMS.append(name)

sep("4. 结论")

if PROBLEMS:
    print(f"  \033[31m发现 {len(PROBLEMS)} 处问题：{', '.join(PROBLEMS)}\033[0m")
    sys.exit(1)
else:
    print("  \033[32m✅ 所有覆盖方法的签名都与库匹配，且不是 final\033[0m")
    sys.exit(0)
