#!/bin/bash
# 用 macOS 自带的 JavaScript 引擎做语法检查
# 原理：用 new Function() 只解析不执行 —— 语法错会抛异常，运行时不执行

set -uo pipefail

cd "/Users/nan/Desktop/始信调音器App" || exit 1

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

echo
echo "${BOLD}JavaScript 语法检查${RESET}"
echo "─" * 66
echo

# ── 先确认 osascript 能用 ──
if ! osascript -l JavaScript -e '"ok"' >/dev/null 2>&1; then
  echo "  ${YELLOW}!${RESET} osascript 不可用，跳过"
  exit 0
fi
echo "  ${GREEN}✓${RESET} osascript 可用"
echo

# ── 从 HTML 里提取所有 <script> 块 ──
python3 - <<'PY'
import re, json, os

BASE = "/Users/nan/Desktop/始信调音器App"
html = open(os.path.join(BASE, "web", "index.html"), encoding="utf-8").read()

# 提取所有 script 块（跳过有 src 的）
blocks = []
for m in re.finditer(r"<script(?![^>]*\bsrc=)[^>]*>(.*?)</script>", html, re.S):
    code = m.group(1)
    if code.strip():
        blocks.append(code)

print(f"  找到 {len(blocks)} 个 script 块")

# 写到临时文件，供 osascript 读取
outdir = "/tmp/metro_js_check"
os.makedirs(outdir, exist_ok=True)
for i, code in enumerate(blocks):
    with open(f"{outdir}/block{i}.js", "w", encoding="utf-8") as f:
        f.write(code)

with open(f"{outdir}/count.txt", "w") as f:
    f.write(str(len(blocks)))
PY

COUNT=$(cat /tmp/metro_js_check/count.txt 2>/dev/null || echo 0)

# ── 逐个检查 ──
for i in $(seq 0 $((COUNT - 1))); do
  F="/tmp/metro_js_check/block$i.js"

  [ -f "$F" ] || continue

  SIZE=$(wc -c < "$F" | tr -d ' ')

  # 用 new Function() 解析（不执行）
  RESULT=$(osascript -l JavaScript -e "
    ObjC.import('Foundation');
    var path = '$F';
    var s = \$.NSString.stringWithContentsOfFileEncodingError(path, \$.NSUTF8StringEncoding, null);
    var code = s.js;
    try {
      new Function(code);
      'SYNTAX_OK';
    } catch (e) {
      'SYNTAX_ERR: ' + e.message;
    }
  " 2>&1)

  if echo "$RESULT" | grep -q "SYNTAX_OK"; then
    printf "  %s 第 %d 块（%s 字节）\n" "${GREEN}✓${RESET}" "$i" "$SIZE"
  else
    printf "  %s 第 %d 块（%s 字节）\n" "${RED}✗${RESET}" "$i" "$SIZE"
    echo "      ${DIM}$(echo "$RESULT" | head -3)${RESET}"
  fi
done

echo
echo "─" * 66
echo
echo "  说明："
echo "    ${DIM}用 new Function() 解析代码 —— 只检查语法，不执行。${RESET}"
echo "    ${DIM}所以 window / document 不存在也不会误报。${RESET}"
echo
