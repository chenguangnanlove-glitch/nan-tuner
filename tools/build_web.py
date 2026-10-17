#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
从原始调音器生成两个文件：

  web/index.html                               → 部署到 Netlify 的网页版（含 PWA + 下载入口）
  android/app/src/main/assets/offline.html     → 打包进 APK 的离线兜底页（无下载入口）

所有改动都是**纯插入**，不删不改原文件的任何一行。

────────────────────────────────────────────────────────────
用法：

  python3 tools/build_web.py
      从桌面上的 `index tuner.html` 重新生成两个文件。
      （你改了桌面那个原文件后，用这个）

  python3 tools/build_web.py --from-web
      以 web/index.html 为准，只重新生成离线版。
      （你直接改了 web/index.html 后，用这个）

  python3 tools/build_web.py --force
      跳过防覆盖检查，强制生成。
────────────────────────────────────────────────────────────

防覆盖保护：脚本会记住上次生成的内容。如果发现 web/index.html
被手动改过，会先提醒你，而不是直接覆盖掉你的修改。
"""

import hashlib
import json
import os
import re
import shutil
import sys

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(os.path.dirname(BASE), "index tuner.html")   # 桌面上的原始文件
OUT_WEB = os.path.join(BASE, "web", "index.html")
OUT_OFFLINE = os.path.join(BASE, "android", "app", "src", "main", "assets", "offline.html")
STATE = os.path.join(BASE, "tools", ".build-state.json")

# 乐器录音：网页版和 APK 各存一份
AUDIO_SRC = os.path.join(BASE, "web", "audio")
AUDIO_APP = os.path.join(BASE, "android", "app", "src", "main", "assets", "audio")

GREEN, RED, YELLOW, DIM, BOLD, RESET = (
    "\033[32m", "\033[31m", "\033[33m", "\033[2m", "\033[1m", "\033[0m"
)

# ══════════════════════════════════════════════════════════════
#  插入片段
# ══════════════════════════════════════════════════════════════

HEAD_EXTRA = """<!-- ===== PWA / 手机 App（由 tools/build_web.py 自动插入） ===== -->
<link rel="manifest" href="/manifest.webmanifest">
<link rel="icon" type="image/png" sizes="64x64" href="/icons/favicon.png">
<link rel="apple-touch-icon" sizes="192x192" href="/icons/icon-192.png">
<meta name="apple-mobile-web-app-status-bar-style" content="black-translucent">
<meta name="apple-mobile-web-app-title" content="始信音乐">
<meta name="mobile-web-app-capable" content="yes">
<meta name="description" content="始信音乐 · 手机调音器：吉他、尤克里里、钢琴调音，精准快速，支持离线使用。">
<meta property="og:type" content="website">
<meta property="og:title" content="始信音乐 · 调音器">
<meta property="og:description" content="精准的手机调音器，支持吉他与尤克里里。">
<meta property="og:image" content="/icons/icon-512.png">
"""

STYLE_EXTRA = """
  /* ===== 手机 App 下载入口（由 tools/build_web.py 自动插入） ===== */
  .app-install-link{
    display:inline-flex;align-items:center;
    font-size:12px;font-weight:500;letter-spacing:.02em;
    color:var(--accent);text-decoration:none;
    padding:6px 13px;border-radius:8px;
    background:var(--accent-soft);
    transition:transform .18s ease,background .18s ease;
    white-space:nowrap;
  }
  .app-install-link:active{transform:scale(.95);background:rgba(212,165,116,.22)}
"""

APP_ROW_ANCHOR = """          <button class="view-btn" data-view="strobe">频闪</button>
        </div>
      </div>"""

APP_ROW_EXTRA = APP_ROW_ANCHOR + """
      <div class="setting-row" id="appRow">
        <span class="setting-label">手机 App</span>
        <a class="app-install-link" href="/download/">下载安装</a>
      </div>"""

TAIL_SCRIPT = """<script>
/* ===== 手机 App / PWA 适配（由 tools/build_web.py 自动插入） ===== */
(function () {
  var bridge  = window.ShixinApp;
  var inApp   = !!(bridge && bridge.isNativeApp && bridge.isNativeApp());
  var isAsset = location.hostname === 'appassets.androidplatform.net';

  /* 已在 App 内运行 → 隐藏“下载安装”入口 */
  if (inApp) {
    var row = document.getElementById('appRow');
    if (row) row.style.display = 'none';
  }

  /* 仅浏览器环境注册 Service Worker，提供离线缓存 */
  if (!inApp && !isAsset && 'serviceWorker' in navigator && location.protocol === 'https:') {
    window.addEventListener('load', function () {
      navigator.serviceWorker.register('/sw.js').catch(function () { /* 静默失败 */ });
    });
  }
})();
</script>
"""


def sha(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()[:16]


def inject(html: str, *, for_app: bool) -> str:
    """把上面几段插入到原 HTML 中。for_app=True 时跳过下载入口。"""
    missing = []
    if "</head>" not in html:
        missing.append("</head>")
    if "</style>" not in html:
        missing.append("</style>")
    if "</body>" not in html:
        missing.append("</body>")
    if not for_app and APP_ROW_ANCHOR not in html:
        missing.append("设置面板锚点（找不到频闪按钮那段）")
    if missing:
        sys.exit(f"{RED}❌ 源文件里找不到这些标记，可能已被改动：{missing}{RESET}")

    html = html.replace("</head>", HEAD_EXTRA + "</head>", 1)
    html = html.replace("</style>", STYLE_EXTRA + "</style>", 1)
    if not for_app:
        html = html.replace(APP_ROW_ANCHOR, APP_ROW_EXTRA, 1)
    html = html.replace("</body>", TAIL_SCRIPT + "</body>", 1)
    return html


def strip_app_row(html: str) -> str:
    """从已生成的网页版里移除「下载安装」入口，用于产出离线版。"""
    pattern = re.compile(
        r'\n[ \t]*<div class="setting-row" id="appRow">.*?</div>[ \t]*\n',
        re.S,
    )
    new, n = pattern.subn("\n", html)
    if n == 0:
        sys.exit(f"{RED}❌ 在 web/index.html 里找不到 appRow 区块，无法生成离线版{RESET}")
    return new


def read(path: str) -> str:
    with open(path, encoding="utf-8") as f:
        return f.read()


def write(path: str, text: str) -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        f.write(text)


def load_state() -> dict:
    try:
        return json.loads(read(STATE))
    except Exception:
        return {}


def save_state(state: dict) -> None:
    write(STATE, json.dumps(state, ensure_ascii=False, indent=2))


def confirm_overwrite(label: str, path: str) -> bool:
    """文件被手动改过 → 问一句再覆盖。"""
    print(f"{YELLOW}⚠  {label} 看起来被你手动改过{RESET}")
    print(f"{DIM}   文件：{path}{RESET}")
    print(f"{DIM}   重新生成会覆盖这些改动。{RESET}")
    print()
    try:
        ans = input("   仍要覆盖吗？输入 y 继续，其它任意键取消 > ").strip().lower()
    except EOFError:
        ans = ""
    print()
    return ans == "y"


def generate_from_source(force: bool) -> int:
    if not os.path.isfile(SRC):
        sys.exit(f"{RED}❌ 找不到桌面上的原文件：{SRC}{RESET}")

    with open(SRC, "rb") as f:
        src_bytes = f.read()
    src_mtime = os.path.getmtime(SRC)

    try:
        src = src_bytes.decode("utf-8")
    except UnicodeDecodeError:
        sys.exit(f"{RED}❌ 原文件不是 UTF-8 编码，请检查：{SRC}{RESET}")

    state = load_state()

    # ---------- 防覆盖检查 ----------
    if not force and os.path.isfile(OUT_WEB) and state.get("out_web"):
        current = sha(read(OUT_WEB))
        if current != state["out_web"]:
            if not confirm_overwrite("web/index.html", OUT_WEB):
                print(f"{DIM}已取消，什么都没改。{RESET}")
                return 0

    web_html = inject(src, for_app=False)
    offline_html = inject(src, for_app=True)

    write(OUT_WEB, web_html)
    write(OUT_OFFLINE, offline_html)

    save_state({
        "source": SRC,
        "source_hash": sha(src),
        "source_mtime": src_mtime,
        "out_web": sha(web_html),
        "out_offline": sha(offline_html),
        "generated_at": __import__("datetime").datetime.now().isoformat(timespec="seconds"),
    })

    print(f"{GREEN}✅ 生成完成{RESET}")
    print()
    print(f"  源文件     {SRC}")
    print(f"            {DIM}{len(src):,} 字符{RESET}")
    print(f"  {GREEN}→{RESET} 站点版     web/index.html")
    print(f"            {DIM}{len(web_html):,} 字符（+{len(web_html) - len(src):,}）{RESET}")
    print(f"  {GREEN}→{RESET} 离线版     android/app/src/main/assets/offline.html")
    print(f"            {DIM}{len(offline_html):,} 字符（+{len(offline_html) - len(src):,}）{RESET}")
    print()
    print(f"{DIM}原始文件的每一行都完整保留，没有任何删改。{RESET}")
    return 0


def generate_offline_only() -> int:
    if not os.path.isfile(OUT_WEB):
        sys.exit(f"{RED}❌ 找不到 {OUT_WEB}，请先跑一次 python3 tools/build_web.py{RESET}")

    web_html = read(OUT_WEB)

    # 如果网页版还没插入过 App 相关代码，先补上
    if 'rel="manifest"' not in web_html:
        print(f"{YELLOW}⚠  web/index.html 里没有 PWA 标记，先补上{RESET}")
        web_html = inject(web_html, for_app=False)
        write(OUT_WEB, web_html)

    offline_html = strip_app_row(web_html)
    write(OUT_OFFLINE, offline_html)

    # 乐器录音同步到 APK assets ——
    # offline.html 从 appassets.androidplatform.net/assets/ 加载，
    # 代码里 fetch('audio/xxx.m4a') 会解析成 /assets/audio/xxx.m4a，
    # 所以音频也必须放进 assets/audio/，否则离线时只剩合成音。
    audio_note = ""
    n = 0
    if os.path.isdir(AUDIO_SRC):
        os.makedirs(AUDIO_APP, exist_ok=True)
        for fn in sorted(os.listdir(AUDIO_SRC)):
            if not fn.lower().endswith((".m4a", ".mp3", ".ogg", ".wav")):
                continue
            src_f = os.path.join(AUDIO_SRC, fn)
            dst_f = os.path.join(AUDIO_APP, fn)
            if (not os.path.isfile(dst_f)
                    or os.path.getsize(src_f) != os.path.getsize(dst_f)
                    or os.path.getmtime(src_f) > os.path.getmtime(dst_f)):
                shutil.copy2(src_f, dst_f)
            n += 1
        audio_note = f"  {GREEN}→{RESET} 乐器录音   assets/audio/  {DIM}{n} 个文件{RESET}"

    state = load_state()
    state["out_web"] = sha(web_html)
    state["out_offline"] = sha(offline_html)
    state["audio_files"] = n
    state["generated_at"] = __import__("datetime").datetime.now().isoformat(timespec="seconds")
    save_state(state)

    print(f"{GREEN}✅ 离线版已同步{RESET}")
    print()
    print(f"  来源       web/index.html  {DIM}{len(web_html):,} 字符{RESET}")
    print(f"  {GREEN}→{RESET} 离线版     android/app/src/main/assets/offline.html")
    print(f"            {DIM}{len(offline_html):,} 字符（已移除下载入口）{RESET}")
    if audio_note:
        print(audio_note)
    return 0


def main() -> int:
    args = sys.argv[1:]
    force = "--force" in args

    if "--from-web" in args:
        return generate_offline_only()
    return generate_from_source(force)


if __name__ == "__main__":
    raise SystemExit(main())
