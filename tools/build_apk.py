#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
本地构建 APK —— 电脑上装了 Android SDK 时用这个，不用等 GitHub。

需要：
  - JDK 17 或更高
  - Android SDK（设好 ANDROID_HOME 或写 android/local.properties）

用法：
    python3 tools/build_apk.py
"""

import os
import platform
import shutil
import subprocess
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
ANDROID = os.path.join(BASE, "android")

GREEN, RED, YELLOW, DIM, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
)


def run(cmd, cwd, env=None):
    print(f"{DIM}$ {' '.join(cmd)}{RESET}")
    return subprocess.run(cmd, cwd=cwd, env=env)


def find_java():
    java = shutil.which("java")
    if not java:
        for cand in [
            "/opt/homebrew/opt/openjdk@17/bin/java",
            "/usr/local/opt/openjdk@17/bin/java",
            "/Library/Java/JavaVirtualMachines/temurin-17.jdk/Contents/Home/bin/java",
        ]:
            if os.path.isfile(cand):
                return cand
        return None
    return java


def find_android_sdk():
    for key in ("ANDROID_HOME", "ANDROID_SDK_ROOT"):
        v = os.environ.get(key)
        if v and os.path.isdir(v):
            return v
    defaults = [
        os.path.expanduser("~/Library/Android/sdk"),
        os.path.expanduser("~/Android/Sdk"),
    ]
    for d in defaults:
        if os.path.isdir(d):
            return d
    return None


def main():
    print(f"\n{BOLD}本地构建 APK{RESET}\n")

    # ---- 环境检查 ----
    java = find_java()
    if java:
        r = subprocess.run([java, "-version"], capture_output=True, text=True)
        ver = (r.stderr or r.stdout).splitlines()[0] if (r.stderr or r.stdout) else "?"
        print(f"  {GREEN}✓{RESET} Java：{ver}")
    else:
        print(f"  {RED}✗{RESET} 没找到 Java")
        print()
        print("  装一个 JDK 17：")
        print(f"    {DIM}brew install --cask temurin@17{RESET}")
        print("  装完重开终端，再跑一次这个脚本。")
        return 1

    sdk = find_android_sdk()
    if sdk:
        print(f"  {GREEN}✓{RESET} Android SDK：{sdk}")
    else:
        print(f"  {RED}✗{RESET} 没找到 Android SDK")
        print()
        print("  两种办法：")
        print(f"    {BOLD}方法一{RESET}（推荐）：装 Android Studio，它会自动装好 SDK")
        print(f"      {DIM}brew install --cask android-studio{RESET}")
        print()
        print(f"    {BOLD}方法二{RESET}：只装命令行工具")
        print(f"      {DIM}brew install --cask android-commandlinetools{RESET}")
        print(f"      {DIM}sdkmanager \"platform-tools\" \"platforms;android-35\" \"build-tools;35.0.0\"{RESET}")
        print()
        print("  装好后如果脚本还是找不到，在 android/local.properties 里写：")
        print(f"    {DIM}sdk.dir=/你的/SDK/路径{RESET}")
        return 1

    gradle = shutil.which("gradle")
    if not gradle:
        print(f"  {YELLOW}!{RESET} 没找到 gradle 命令")

    # ---- 读取版本号 ----
    import json
    with open(os.path.join(BASE, "web", "app-version.json"), encoding="utf-8") as f:
        ver = json.load(f)
    vcode, vname = ver["versionCode"], ver["versionName"]
    print(f"  {GREEN}✓{RESET} 版本：{vname} (versionCode {vcode})")

    # ---- 读取签名配置 ----
    ks = os.path.join(BASE, "tools", "keystore", "shixin-tuner.p12")
    info = os.path.join(BASE, "tools", "keystore", "密钥信息.txt")
    env = os.environ.copy()

    if os.path.isfile(ks) and os.path.isfile(info):
        with open(info, encoding="utf-8") as f:
            text = f.read()

        def grab(label):
            import re
            m = re.search(rf"{label}\s*[：:]\s*(\S+)", text)
            return m.group(1).strip() if m else None

        env["SHIXIN_KEYSTORE"] = ks
        env["SHIXIN_STORE_PASSWORD"] = grab("密钥库密码") or ""
        env["SHIXIN_KEY_PASSWORD"] = grab("密钥密码") or ""
        env["SHIXIN_KEY_ALIAS"] = grab("密钥别名") or "shixin"
        print(f"  {GREEN}✓{RESET} 使用正式签名密钥")
    else:
        print(f"  {YELLOW}!{RESET} 没找到签名密钥，将用 debug 签名（只能自己测试，不能分发）")
        print(f"      {DIM}先跑：bash tools/make_keystore.sh{RESET}")

    # ---- 构建 ----
    print(f"\n{BOLD}开始构建…{RESET}\n")
    cmd = [
        gradle or ("./gradlew" if os.path.isfile(os.path.join(ANDROID, "gradlew")) else "gradle"),
        "assembleRelease",
        f"-PversionCode={vcode}",
        f"-PversionName={vname}",
        "--no-daemon",
    ]
    r = run(cmd, cwd=ANDROID, env=env)
    if r.returncode != 0:
        print(f"\n{RED}构建失败。{RESET}")
        print(f"{DIM}常见原因：SDK 平台版本没装、Java 版本不对、网络下载依赖失败。{RESET}")
        return r.returncode

    # ---- 收集产物 ----
    out_dir = os.path.join(ANDROID, "app", "build", "outputs", "apk", "release")
    apks = []
    if os.path.isdir(out_dir):
        apks = [f for f in os.listdir(out_dir) if f.endswith(".apk")]

    if not apks:
        print(f"\n{RED}没找到生成的 APK{RESET}")
        return 1

    src = os.path.join(out_dir, apks[0])
    dst_dir = os.path.join(BASE, "web", "download")
    os.makedirs(dst_dir, exist_ok=True)
    dst = os.path.join(dst_dir, "shixin-tuner.apk")
    shutil.copy2(src, dst)

    size = os.path.getsize(dst)
    print(f"\n{GREEN}{BOLD}✅ 构建完成{RESET}")
    print()
    print(f"  APK 位置：{dst}")
    print(f"  大小    ：{size / 1024 / 1024:.1f} MB")
    print()
    print(f"{DIM}装到手机上测试：")
    print(f"  1. 用数据线连接手机（已开 USB 调试）")
    print(f"     adb install -r \"{dst}\"")
    print(f"  2. 或者把 APK 传到手机，点开安装")
    print()
    print(f"  确认没问题后，把整个项目推到 GitHub，")
    print(f"  Netlify 会自动发布 web/ 目录，手机就能从网页下载了。{RESET}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
