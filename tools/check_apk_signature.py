#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
检查 APK 的签名方案（v1 / v2 / v3）。

为什么要专门写这个：
  Android 7.0+ 默认使用 v2/v3 签名方案，签名信息不在 META-INF/ 目录里，
  而是存在 ZIP 中央目录之前的一个特殊区块（APK Signing Block）。
  只看 META-INF/ 会得出「没有签名」的错误结论。

APK Signing Block 结构：
  [8 字节]  区块大小（不含这 8 字节）
  [若干]    ID-值对，其中 ID 0x7109871a = v2 签名，0xf05368c0 = v3 签名
  [8 字节]  重复的区块大小
  [16 字节] 魔数 "APK Sig Block 42"
"""

import os
import struct
import sys

APK = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "web", "download", "shixin-tuner.apk",
)

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"

MAGIC = b"APK Sig Block 42"

# 签名方案 ID
SCHEMES = {
    0x7109871a: ("v2 签名", "Android 7.0+ 使用"),
    0xf05368c0: ("v3 签名", "Android 9+ 使用，支持密钥轮换"),
    0x1b93ad61: ("v3.1 签名", "Android 13+ 使用"),
    0x42726577: ("签名证书填充", "辅助数据"),
    0x42726576: ("额外属性", "辅助数据"),
    0x2146444e: ("源戳（Source Stamp）", "v1 签名的源信息"),
}

print()
print(f"{BOLD}APK 签名检查{RESET}")
print("─" * 70)

if not os.path.isfile(APK):
    print(f"{RED}✗ 找不到 APK：{APK}{RESET}")
    sys.exit(1)

size = os.path.getsize(APK)
print(f"  文件：{os.path.basename(APK)}")
print(f"  大小：{size:,} 字节（{size / 1024 / 1024:.2f} MB）")
print()

with open(APK, "rb") as f:
    data = f.read()

# ══════════════════════════════════════════════════════════
#  1. 找 ZIP 的 End of Central Directory (EOCD)
# ══════════════════════════════════════════════════════════
print(f"{BOLD}1. 定位 ZIP 结构{RESET}")
print()

eocd_pos = -1
# EOCD 签名 0x06054b50，从文件末尾往前找（注释最多 65535 字节）
search_start = max(0, size - 65557)
idx = data.rfind(b"PK\x05\x06", search_start)
if idx < 0:
    print(f"  {RED}✗ 找不到 EOCD，文件可能损坏{RESET}")
    sys.exit(1)

eocd_pos = idx
cd_size, cd_offset = struct.unpack("<II", data[eocd_pos + 12:eocd_pos + 20])
print(f"  EOCD 位置      ：{eocd_pos:,}")
print(f"  中央目录大小   ：{cd_size:,} 字节")
print(f"  中央目录偏移   ：{cd_offset:,}")
print(f"  文件总大小     ：{size:,}")

# ══════════════════════════════════════════════════════════
#  2. 检查 APK Signing Block（位于中央目录之前）
# ══════════════════════════════════════════════════════════
print()
print(f"{BOLD}2. APK Signing Block（v2/v3 签名所在）{RESET}")
print()

# 魔数应该在中央目录紧邻的前面
if cd_offset >= 32:
    magic_check = data[cd_offset - 16:cd_offset]
    if magic_check == MAGIC:
        print(f"  {GREEN}✓ 找到签名区块魔数{RESET}：{MAGIC.decode()}")
        has_signing_block = True
    else:
        print(f"  {RED}✗ 中央目录前没有签名区块{RESET}")
        print(f"     那块内容是：{magic_check!r}")
        has_signing_block = False
else:
    print(f"  {RED}✗ 文件太小，不可能有签名区块{RESET}")
    has_signing_block = False

if has_signing_block:
    # 区块大小在魔数前面 8 字节（其实是区块末尾的大小字段）
    block_size_2 = struct.unpack("<Q", data[cd_offset - 24:cd_offset - 16])[0]
    block_start = cd_offset - 8 - block_size_2
    block_size_1 = struct.unpack("<Q", data[block_start:block_start + 8])[0]

    print(f"  区块起始位置   ：{block_start:,}")
    print(f"  区块大小       ：{block_size_1:,} 字节")

    if block_size_1 != block_size_2:
        print(f"  {RED}✗ 区块大小字段不一致（{block_size_1} vs {block_size_2}）{RESET}")
    else:
        print(f"  {GREEN}✓ 区块大小字段一致{RESET}")

    # 遍历区块里的 ID-值对
    print()
    print(f"{BOLD}3. 区块内的签名方案{RESET}")
    print()

    pos = block_start + 8
    end = cd_offset - 24
    found_schemes = []

    while pos + 12 <= end:
        pair_len = struct.unpack("<Q", data[pos:pos + 8])[0]
        if pair_len < 4 or pos + 8 + pair_len > end + 8:
            break
        pair_id = struct.unpack("<I", data[pos + 8:pos + 12])[0]
        found_schemes.append((pair_id, pair_len))
        pos += 8 + pair_len

    if not found_schemes:
        print(f"  {YELLOW}!{RESET} 区块里没有解析出签名方案")
    else:
        for pid, plen in found_schemes:
            name, note = SCHEMES.get(pid, (f"未知方案 (0x{pid:08x})", ""))
            mark = f"{GREEN}✓{RESET}" if pid in (0x7109871a, 0xf05368c0, 0x1b93ad61) else f"{DIM}·{RESET}"
            print(f"  {mark} {name:<20} {DIM}({plen:,} 字节)  {note}{RESET}")

# ══════════════════════════════════════════════════════════
#  4. v1 签名（META-INF）
# ══════════════════════════════════════════════════════════
print()
print(f"{BOLD}4. v1 签名（META-INF 目录）{RESET}")
print()

import zipfile
zf = zipfile.ZipFile(APK)
names = zf.namelist()
v1_files = [n for n in names if n.startswith("META-INF/") and
            (n.endswith((".RSA", ".DSA", ".EC", ".SF", ".MF")))]

if v1_files:
    for v in sorted(v1_files):
        print(f"  {GREEN}✓{RESET} {v}")
else:
    print(f"  {DIM}· 没有 v1 签名文件（现代构建通常省略，属正常）{RESET}")

# ══════════════════════════════════════════════════════════
#  结论
# ══════════════════════════════════════════════════════════
print()
print("─" * 70)
print()

modern = has_signing_block
if modern:
    print(f"{GREEN}{BOLD}✅ APK 已用现代方案签名，可以正常安装{RESET}")
    print()
    print(f"  {DIM}Android 7.0 及以上优先使用 v2/v3 签名，")
    print(f"  这类签名不在 META-INF 里，所以只看目录结构会误判。{RESET}")
    sys.exit(0)
else:
    print(f"{RED}{BOLD}✗ APK 没有签名，手机可能拒绝安装{RESET}")
    sys.exit(1)
