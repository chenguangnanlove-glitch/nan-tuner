#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
一键配置 —— 把站点地址写进所有需要它的地方。

用法：
    python3 tools/setup.py                      # 交互式，会问你要域名
    python3 tools/setup.py shixin.netlify.app   # 直接指定
"""

import os
import re
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

GREEN = "\033[32m"
RED = "\033[31m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


def normalize(raw: str) -> str:
    """把用户输入的各种写法统一成 https://域名（不带结尾斜杠）"""
    s = raw.strip()
    s = re.sub(r"^https?://", "", s, flags=re.I)   # 去掉协议
    s = s.rstrip("/")                               # 去掉结尾斜杠
    s = s.split("/")[0]                             # 去掉路径
    return s


def valid(host: str) -> bool:
    if not host or " " in host:
        return False
    if host.startswith("localhost") or re.match(r"^\d+\.\d+\.\d+\.\d+$", host):
        return False
    return "." in host and len(host) > 3


def ask() -> str:
    print(f"{BOLD}请输入你的 Netlify 站点地址{RESET}")
    print(f"{DIM}例如：shixin.netlify.app  或  tuner.你的域名.com{RESET}")
    print(f"{DIM}（不用带 https://，脚本会自动补上）{RESET}")
    print()
    while True:
        raw = input("域名 > ").strip()
        host = normalize(raw)
        if valid(host):
            return host
        print(f"{RED}这个看起来不对，再试一次。{RESET}")


def update_file(rel, pattern, repl, label):
    path = os.path.join(BASE, rel)
    if not os.path.isfile(path):
        print(f"  {RED}✗{RESET} 找不到 {rel}")
        return False
    with open(path, encoding="utf-8") as f:
        text = f.read()
    new, n = re.subn(pattern, repl, text, flags=re.M)
    if n == 0:
        print(f"  {RED}✗{RESET} {label}：没有匹配到要修改的位置")
        return False
    if new == text:
        print(f"  {DIM}={RESET} {label}：已是目标值，无需改动")
        return True
    with open(path, "w", encoding="utf-8") as f:
        f.write(new)
    print(f"  {GREEN}✓{RESET} {label}")
    return True


def main():
    if len(sys.argv) > 1:
        host = normalize(sys.argv[1])
        if not valid(host):
            sys.exit(f"{RED}域名格式不对：{sys.argv[1]}{RESET}")
    else:
        print()
        host = ask()

    url = f"https://{host}"

    print()
    print(f"{BOLD}正在把站点地址写入 {url}{RESET}")
    print()

    results = []

    # 1. gradle.properties —— App 打包时读取
    results.append(update_file(
        "android/gradle.properties",
        r"^shixin\.siteUrl\s*=.*$",
        f"shixin.siteUrl={url}",
        "android/gradle.properties  → App 打开的网址",
    ))

    # 2. app-version.json 里的 apk 路径保持相对，无需改
    # 3. 检查一下流水线无需改（用项目属性传入）

    print()
    if all(results):
        print(f"{GREEN}{BOLD}✅ 配置完成{RESET}")
        print()
        print(f"  App 将打开：{url}")
        print(f"  下载页地址：{url}/download/")
        print()
        print(f"{DIM}下一步：")
        print(f"  1. 生成签名密钥   bash tools/make_keystore.sh")
        print(f"  2. 上传到 GitHub  见 操作说明.md")
        print(f"  3. 构建 APK        GitHub Actions 自动完成{RESET}")
        print()
    else:
        print(f"{RED}有项目没配置成功，请检查上面的输出。{RESET}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
