#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
上线前自检 —— 检查工程里所有配置是否一致、有没有漏掉必须改的地方。

用法：  python3 tools/check.py
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

OK, WARN, FAIL = "✅", "⚠️ ", "❌"
problems = []
warnings = []
passed = 0


def ok(msg):
    global passed
    passed += 1
    print(f"  {OK} {msg}")


def warn(msg):
    warnings.append(msg)
    print(f"  {WARN} {msg}")


def fail(msg):
    problems.append(msg)
    print(f"  {FAIL} {msg}")


def exists(rel):
    return os.path.isfile(os.path.join(BASE, rel))


def read(rel):
    with open(os.path.join(BASE, rel), encoding="utf-8") as f:
        return f.read()


def section(title):
    print(f"\n\033[1m{title}\033[0m")


# ══════════════════════════════════════════════════════════════
section("1. 站点地址配置")

site_url = ""
props = read("android/gradle.properties")
m = re.search(r"^shixin\.siteUrl\s*=\s*(\S+)", props, re.M)
if not m:
    fail("gradle.properties 里找不到 shixin.siteUrl")
else:
    site_url = m.group(1).strip()
    if "your-site" in site_url:
        fail(f"站点地址还是占位符：{site_url}")
        print("     → 请改成你 Netlify 的真实域名，例如 https://shixin.netlify.app")
    elif not site_url.startswith("https://"):
        fail(f"站点地址必须是 https:// 开头（安卓只允许安全连接使用麦克风）：{site_url}")
    elif site_url.endswith("/"):
        warn(f"站点地址结尾多了斜杠：{site_url}  → 建议去掉")
    else:
        ok(f"站点地址：{site_url}")

# ══════════════════════════════════════════════════════════════
section("2. 关键文件是否齐全")

required = [
    ("web/index.html", "站点主页（调音器）"),
    ("web/manifest.webmanifest", "PWA 清单"),
    ("web/sw.js", "Service Worker（离线缓存）"),
    ("web/app-version.json", "版本信息（App 靠它检测更新）"),
    ("web/download/index.html", "下载页"),
    ("web/icons/icon-192.png", "图标 192"),
    ("web/icons/icon-512.png", "图标 512"),
    ("web/icons/icon-maskable-512.png", "图标 maskable"),
    ("web/icons/favicon.png", "图标 favicon"),
    ("android/settings.gradle", "Gradle 设置"),
    ("android/build.gradle", "Gradle 顶层构建"),
    ("android/gradle.properties", "Gradle 属性"),
    ("android/app/build.gradle", "App 构建配置"),
    ("android/app/src/main/AndroidManifest.xml", "安卓清单"),
    ("android/app/src/main/assets/offline.html", "内置离线页"),
    ("android/app/src/main/java/com/shixin/tuner/MainActivity.java", "App 主程序"),
    ("netlify.toml", "Netlify 配置"),
    (".github/workflows/build-apk.yml", "自动构建流水线"),
    (".gitignore", "Git 忽略规则"),
]
for rel, desc in required:
    if exists(rel):
        ok(desc)
    else:
        fail(f"缺少 {desc}：{rel}")

# ══════════════════════════════════════════════════════════════
section("3. 版本号是否一致")

try:
    ver = json.loads(read("web/app-version.json"))
    vcode = int(ver.get("versionCode", 0))
    vname = str(ver.get("versionName", ""))
    apk_path = str(ver.get("apk", ""))

    if vcode < 1:
        fail(f"versionCode 必须 ≥ 1，当前 {vcode}")
    else:
        ok(f"versionCode = {vcode}")

    if not re.fullmatch(r"\d+\.\d+\.\d+", vname):
        warn(f"versionName 建议用 x.y.z 格式，当前：{vname}")
    else:
        ok(f"versionName = {vname}")

    if not apk_path.endswith(".apk"):
        fail(f"apk 字段必须是 .apk 路径，当前：{apk_path}")
    else:
        target = "web" + (apk_path if apk_path.startswith("/") else "/" + apk_path)
        if exists(target):
            ok(f"APK 已就位：{apk_path}")
        else:
            warn(f"APK 还没生成：{target}")
            print("     → 首次需要跑一次 GitHub Actions 构建（或本地构建）")
except Exception as e:
    fail(f"app-version.json 读不了：{e}")

# ══════════════════════════════════════════════════════════════
section("4. 安卓清单权限")

try:
    tree = ET.parse(os.path.join(BASE, "android/app/src/main/AndroidManifest.xml"))
    root = tree.getroot()
    NS = "{http://schemas.android.com/apk/res/android}"

    perms = {p.get(NS + "name") for p in root.findall("uses-permission")}
    for need, why in [
        ("android.permission.RECORD_AUDIO", "麦克风（调音必需）"),
        ("android.permission.INTERNET", "联网加载网页"),
        ("android.permission.ACCESS_NETWORK_STATE", "判断是否断网"),
    ]:
        if need in perms:
            ok(why)
        else:
            fail(f"清单里缺少权限：{need}（{why}）")

    app = root.find("application")
    if app is None:
        fail("清单里找不到 <application>")
    else:
        if app.get(NS + "usesCleartextTraffic") == "false":
            ok("已禁止明文流量")
        else:
            warn("建议设置 usesCleartextTraffic=\"false\"")

        acts = app.findall("activity")
        has_launcher = any(
            any(
                (c.get(NS + "name") or "").endswith("LAUNCHER")
                for f in a.findall("intent-filter")
                for c in f.findall("category")
            )
            for a in acts
        )
        if has_launcher:
            ok("已声明桌面图标入口")
        else:
            fail("没有启动入口，装完在桌面找不到图标")
except FileNotFoundError:
    fail("AndroidManifest.xml 不存在")
except ET.ParseError as e:
    fail(f"AndroidManifest.xml 格式错误：{e}")

# ══════════════════════════════════════════════════════════════
section("5. 代码与资源引用")

try:
    java = read("android/app/src/main/java/com/shixin/tuner/MainActivity.java")

    if "BuildConfig.SITE_URL" in java:
        ok("主程序使用可配置的站点地址")
    else:
        warn("主程序没有引用 BuildConfig.SITE_URL")

    if "appassets.androidplatform.net/assets/offline.html" in java:
        ok("离线兜底页路径正确")
    else:
        fail("离线页路径不对，断网时会白屏")

    if "RESOURCE_AUDIO_CAPTURE" in java:
        ok("已接管麦克风授权")
    else:
        fail("没有处理网页的麦克风授权请求，调音会失败")

    if "setJavaScriptEnabled(true)" in java:
        ok("已启用 JavaScript")
    else:
        fail("没有启用 JavaScript，网页跑不起来")

    if "FLAG_KEEP_SCREEN_ON" in java:
        ok("调音时屏幕保持常亮")
    else:
        warn("没有保持屏幕常亮，调音中途可能熄屏")

    if "appassets.androidplatform.net" in java and "addPathHandler" in java:
        ok("离线页走安全上下文（麦克风可用）")
    else:
        fail("离线页没有走 WebViewAssetLoader，file:// 下麦克风会被拒")
except FileNotFoundError:
    fail("找不到 MainActivity.java")

# ══════════════════════════════════════════════════════════════
section("6. 网页与离线页")

for rel, label, want_download_btn in [
    ("web/index.html", "站点版", True),
    ("android/app/src/main/assets/offline.html", "离线版", False),
]:
    if not exists(rel):
        fail(f"{label}不存在：{rel}")
        continue
    html = read(rel)
    if len(html) < 5000:
        fail(f"{label}内容异常短（{len(html)} 字符），可能没生成成功")
    else:
        ok(f"{label}内容完整（{len(html):,} 字符）")

    if 'id="appRow"' in html:
        if want_download_btn:
            ok(f"{label}有下载入口")
        else:
            warn("离线版不该有下载入口")
    else:
        if want_download_btn:
            fail("站点版缺少「下载安装」入口")
        else:
            ok(f"{label}没有多余的下载入口")

    for marker in ["strobeCanvas", "getUserMedia", "noteName"]:
        if marker not in html:
            fail(f"{label}缺少调音功能代码：{marker}")

# ══════════════════════════════════════════════════════════════
section("7. PWA 清单与缓存")

try:
    mf = json.loads(read("web/manifest.webmanifest"))
    for key in ["name", "short_name", "start_url", "display", "icons", "theme_color"]:
        if key in mf:
            ok(f"清单字段 {key}")
        else:
            fail(f"清单缺少字段：{key}")
    if mf.get("display") in ("standalone", "fullscreen"):
        ok("以独立 App 形式打开（不显示浏览器地址栏）")
    sizes = {i.get("sizes") for i in mf.get("icons", [])}
    if "512x512" in sizes:
        ok("含 512 图标（安装到桌面必需）")
    else:
        fail("缺少 512x512 图标")
    if any(i.get("purpose") == "maskable" for i in mf.get("icons", [])):
        ok("含 maskable 图标（圆形图标不变形）")
    else:
        warn("建议加 maskable 图标")
except Exception as e:
    fail(f"PWA 清单有问题：{e}")

try:
    sw = read("web/sw.js")
    for marker in ["install", "activate", "fetch", "app-version"]:
        if marker in sw:
            ok(f"Service Worker 处理了 {marker}")
    if re.search(r"\.apk", sw):
        ok("APK 不进入缓存（保证下载到最新版）")
    else:
        warn("Service Worker 没有排除 APK，可能缓存到旧安装包")
except FileNotFoundError:
    fail("找不到 sw.js")

# ══════════════════════════════════════════════════════════════
section("8. 签名密钥")

ks_dir = os.path.join(BASE, "tools", "keystore")
ks_file = os.path.join(ks_dir, "shixin-tuner.p12")
info_file = os.path.join(ks_dir, "密钥信息.txt")
b64_file = os.path.join(ks_dir, "KEYSTORE_BASE64.txt")

if os.path.isfile(ks_file):
    ok(f"密钥库已生成（{os.path.getsize(ks_file):,} 字节）")
    if os.path.isfile(info_file):
        ok("密码信息已保存")
    else:
        fail("密钥库在，但密码信息丢了 —— 无法继续")
    if os.path.isfile(b64_file):
        ok("GitHub 用的 base64 已生成")
    else:
        warn("缺少 KEYSTORE_BASE64.txt")
else:
    warn("还没有生成签名密钥")
    print("     → 运行：bash tools/make_keystore.sh")

gi = read(".gitignore") if exists(".gitignore") else ""
if "*.p12" in gi or "*.keystore" in gi or "keystore" in gi:
    ok("密钥已排除在 Git 之外（不会被上传）")
else:
    fail("危险：密钥可能被提交到 GitHub！请在 .gitignore 里排除")

# ══════════════════════════════════════════════════════════════
section("9. 自动构建流水线")

try:
    yml = read(".github/workflows/build-apk.yml")
    for marker, desc in [
        ("workflow_dispatch", "支持手动触发"),
        ("KEYSTORE_BASE64", "会还原签名密钥"),
        ("assembleRelease", "构建 release 版本"),
        ("upload-artifact", "保留构建产物"),
        ("web/download", "APK 输出到下载目录"),
        ("PBE", "—"),
    ]:
        if marker == "PBE":
            continue
        if marker in yml:
            ok(desc)
        else:
            fail(f"流水线缺少：{desc}")
    if "git push" in yml:
        ok("构建后自动发布（Netlify 会跟着更新）")
    else:
        warn("流水线不会自动发布，需要手动下载 APK")
except FileNotFoundError:
    fail("找不到 .github/workflows/build-apk.yml")

# ══════════════════════════════════════════════════════════════
section("10. Netlify 配置")

try:
    nt = read("netlify.toml")
    if 'publish = "web"' in nt:
        ok("发布目录指向 web/")
    else:
        fail("netlify.toml 里 publish 不是 \"web\"")
    if "application/vnd.android.package-archive" in nt:
        ok("APK 的 MIME 类型已声明（手机才能正确识别为安装包）")
    else:
        fail("缺少 APK 的 MIME 类型声明，手机可能把安装包当普通文件")
    if "app-version.json" in nt and "no-store" in nt:
        ok("版本信息不被缓存（否则检测不到更新）")
    else:
        warn("版本信息建议设为不缓存")
    if "Permissions-Policy" in nt and "microphone=(self)" in nt:
        ok("已允许本站使用麦克风")
    else:
        fail("Permissions-Policy 没允许麦克风")
except FileNotFoundError:
    fail("找不到 netlify.toml")

# ══════════════════════════════════════════════════════════════
section("11. Shell 脚本中文兼容性")

# bash 解析 $VAR 时，如果后面紧跟中文标点，会把中文字节当成变量名的一部分，
# 导致 "unbound variable" 报错。必须写成 ${VAR}。
import re as _re

_shell_files = []
for _dp, _dn, _fn in os.walk(BASE):
    _dn[:] = [d for d in _dn if d not in (".git", "build", ".gradle")]
    for _f in _fn:
        if _f.endswith((".sh", ".bash", ".command")):
            _shell_files.append(os.path.join(_dp, _f))

_PAT = _re.compile(r"\$(?!\{)([A-Za-z_][A-Za-z0-9_]*)([^\x00-\x7F])")
_i18n_bad = 0
for _p in _shell_files:
    _rel = os.path.relpath(_p, BASE)
    try:
        with open(_p, encoding="utf-8") as _f:
            for _i, _line in enumerate(_f, 1):
                for _m in _PAT.finditer(_line):
                    _i18n_bad += 1
                    fail(f"{_rel} 第 {_i} 行：${_m.group(1)} 后紧跟 {_m.group(2)!r}，"
                         f"应写作 ${{{_m.group(1)}}}")
    except Exception:
        pass

if _i18n_bad == 0:
    ok(f"{len(_shell_files)} 个 shell 脚本都没有「$VAR 紧跟中文」的隐患")

# ══════════════════════════════════════════════════════════════
print("\n" + "═" * 62)
if problems:
    print(f"\033[31m❌ 发现 {len(problems)} 个必须处理的问题：\033[0m")
    for i, p in enumerate(problems, 1):
        print(f"   {i}. {p}")
if warnings:
    print(f"\033[33m⚠️  有 {len(warnings)} 条提醒（不阻塞，但建议看看）：\033[0m")
    for i, w in enumerate(warnings, 1):
        print(f"   {i}. {w}")
if not problems:
    print(f"\033[32m🎉 全部关键检查通过（{passed} 项）\033[0m")
    if warnings:
        print("   上面那些提醒不影响先跑起来，可以之后慢慢优化。")
print("═" * 62)

sys.exit(1 if problems else 0)
