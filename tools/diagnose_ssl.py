#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
诊断 SSL 证书问题，并给出结论：
  A. 是 Python 自己的证书库没装（最常见，好修）
  B. 还是代理在做中间人拦截（CLASH MITM，需要改配置）
"""

import os
import shutil
import socket
import ssl
import subprocess
import sys


def sep(title):
    print()
    print(f"\033[1m{title}\033[0m")
    print("─" * 58)


sep("1. Python 环境")

print(f"  版本      : {sys.version.split()[0]}")
print(f"  可执行文件: {sys.executable}")
print(f"  SSL 版本  : {ssl.OPENSSL_VERSION}")

# 这是不是 python.org 装的？
IS_PYTHON_ORG = "/Library/Frameworks/Python.framework" in sys.executable
print(f"  来源      : {'python.org 官方安装包' if IS_PYTHON_ORG else '其它（brew / 系统）'}")

sep("2. Python 的证书库")

try:
    import certifi

    cafile = certifi.where()
    exists = os.path.isfile(cafile)
    size = os.path.getsize(cafile) if exists else 0
    certs = certifi.contents().count("BEGIN CERTIFICATE") if exists else 0
    print(f"  certifi   : 已安装 {certifi.__version__}")
    print(f"  证书文件  : {cafile}")
    print(f"  状态      : {'存在' if exists else '缺失'}，{certs} 张证书，{size:,} 字节")
    HAS_CERTIFI = True
except ImportError:
    print("  certifi   : 未安装 ← 这可能就是根因")
    HAS_CERTIFI = False

# 系统默认路径
default_paths = ssl.get_default_verify_paths()
print(f"  默认 cafile: {default_paths.cafile or '（无）'}")
print(f"  默认 capath: {default_paths.capath or '（无）'}")
if default_paths.cafile:
    print(f"  该文件     : {'存在' if os.path.isfile(default_paths.cafile) else '不存在'}")

sep("3. 实际握手测试")

HOST = "github.com"

def probe(label, ctx):
    try:
        s = socket.create_connection((HOST, 443), timeout=12)
        with ctx.wrap_socket(s, server_hostname=HOST):
            print(f"  {label}: 成功 ✓")
        return True
    except Exception as e:
        name = type(e).__name__
        msg = str(e)
        if "CERTIFICATE_VERIFY_FAILED" in msg:
            print(f"  {label}: 证书验证失败 ✗")
        else:
            print(f"  {label}: {name}: {msg[:80]}")
        return False


probe("默认配置  ", ssl.create_default_context())
if HAS_CERTIFI:
    probe("certifi   ", ssl.create_default_context(cafile=certifi.where()))
probe("不验证    ", ssl._create_unverified_context() if hasattr(ssl, "_create_unverified_context")
      else ssl.create_default_context())

sep("4. 证书颁发者（判断有无中间人）")

CERT_SCRIPT = """
import socket, ssl
ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
ctx.check_hostname = False
ctx.verify_mode = ssl.CERT_NONE
s = socket.create_connection(("github.com", 443), timeout=12)
ss = ctx.wrap_socket(s, server_hostname="github.com")
der = ss.getpeercert(binary_form=True)
print("CERT_DER_LEN", len(der))
"""

try:
    out = subprocess.run(
        [sys.executable, "-c", CERT_SCRIPT],
        capture_output=True, text=True, timeout=25
    )
    print(f"  握手结果: {out.stdout.strip() or out.stderr.strip()[:120]}")
except Exception as e:
    print(f"  握手异常: {e}")

# 用 openssl 看证书链（更详细）
openssl = shutil.which("openssl")
if openssl:
    try:
        r = subprocess.run(
            ["bash", "-c",
             f'echo | {openssl} s_client -connect github.com:443 '
             f'-servername github.com 2>/dev/null | {openssl} x509 -noout -issuer -subject 2>/dev/null'],
            capture_output=True, text=True, timeout=25
        )
        if r.stdout.strip():
            for line in r.stdout.strip().splitlines():
                print(f"  {line.strip()}")
        else:
            print("  （openssl 没返回证书信息）")
    except Exception as e:
        print(f"  openssl 异常: {e}")

sep("5. 结论")

print()
if IS_PYTHON_ORG and not HAS_CERTIFI:
    print("  原因 A：python.org 版 Python 没装根证书")
    print()
    print("  这是 macOS 上的经典问题。python.org 的安装包不带证书库，")
    print("  需要手动跑一次官方的安装脚本。")
    print()
    print("  修法（二选一）：")
    print("    1. 跑官方脚本（推荐，一次搞定）：")
    print("       /Applications/Python 3.14/Install\\ Certificates.command")
    print()
    print("    2. 只装 certifi：")
    print("       pip3 install certifi")
else:
    print("  请把上面的输出发我，我来判断。")
    print()
    print("  如果 openssl 显示的颁发者不是 DigiCert / Sectigo / Let's Encrypt")
    print("  这类知名 CA，而是 Clash 相关名字，那就是代理在做中间人。")

print()
