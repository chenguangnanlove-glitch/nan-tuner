#!/bin/bash
# 节拍器最终完整验证

set -uo pipefail

cd "/Users/nan/Desktop/始信调音器App" || exit 1

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

pass=0
fail=0

ok()   { echo "  ${GREEN}✓${RESET} $*"; pass=$((pass+1)); }
bad()  { echo "  ${RED}✗${RESET} $*"; fail=$((fail+1)); }
info() { echo "  ${DIM}·${RESET} $*"; }
head_() { echo; echo "${BOLD}$*${RESET}"; }

echo
echo "${BOLD}════════════════════════════════════════════════${RESET}"
echo "${BOLD}   节拍器 · 最终验证${RESET}"
echo "${BOLD}════════════════════════════════════════════════${RESET}"

# ════════════════════════════════════════════════════════
head_ "1. 文件完整性"

for f in web/index.html android/app/src/main/assets/offline.html \
         tools/metronome_core.js tools/metronome_engine.js; do
  if [ -f "$f" ]; then
    ok "$(basename "$f")  $(wc -c < "$f" | tr -d ' ') 字节"
  else
    bad "缺少 $f"
  fi
done

# ════════════════════════════════════════════════════════
head_ "2. 三方同步"

WEB_METRO=$(grep -c "pageMetro" web/index.html 2>/dev/null || echo 0)
OFF_METRO=$(grep -c "pageMetro" android/app/src/main/assets/offline.html 2>/dev/null || echo 0)

if [ "$WEB_METRO" -gt 0 ]; then ok "网页版含节拍器"; else bad "网页版缺节拍器"; fi
if [ "$OFF_METRO" -gt 0 ]; then ok "离线版含节拍器"; else bad "离线版缺节拍器"; fi

# 主色一致
WEB_ACCENT=$(grep -m1 -o "\-\-accent:#[0-9a-f]*" web/index.html)
OFF_ACCENT=$(grep -m1 -o "\-\-accent:#[0-9a-f]*" android/app/src/main/assets/offline.html)
if [ "$WEB_ACCENT" = "$OFF_ACCENT" ]; then
  ok "配色一致（${WEB_ACCENT}）"
else
  bad "配色不一致：${WEB_ACCENT} vs ${OFF_ACCENT}"
fi

# ════════════════════════════════════════════════════════
head_ "3. HTML 结构"

OUT=$(python3 tools/verify_structure.py 2>&1)
if echo "$OUT" | grep -q "结构完整"; then
  ok "标签配对、元素齐全、原有内容完整"
else
  bad "结构有问题"
  echo "$OUT" | tail -8 | sed 's/^/      /'
fi

# ════════════════════════════════════════════════════════
head_ "4. JS 语法"

OUT=$(bash tools/check_js.sh 2>&1)
if echo "$OUT" | grep -qE "✗"; then
  bad "有语法错误"
  echo "$OUT" | grep -A 2 "✗" | sed 's/^/      /'
else
  N=$(echo "$OUT" | grep -c "第 [0-9]* 块")
  ok "$N 个 script 块语法正确"
fi

# ════════════════════════════════════════════════════════
head_ "5. 核心逻辑（实际运行 JS）"

OUT=$(python3 tools/test_metronome.py 2>&1)
if echo "$OUT" | grep -q "全部通过"; then
  ok "$(echo "$OUT" | grep -oE '[0-9]+ 项全部通过')"
else
  bad "测试失败"
  echo "$OUT" | tail -8 | sed 's/^/      /'
fi

# ════════════════════════════════════════════════════════
head_ "6. 元素引用"

OUT=$(python3 tools/check_ids.py 2>&1)
if echo "$OUT" | grep -q "所有被引用的 id 都已定义"; then
  ok "JS 引用的 id 全部存在"
else
  bad "有 id 引用不到"
fi

if echo "$OUT" | grep -q "19/19"; then
  ok "19 个节拍器元素齐全"
fi

head_ "6.5 圆环拖动逻辑"

OUT=$(python3 tools/test_drag.py 2>&1)
if echo "$OUT" | grep -q "全部通过"; then
  ok "$(echo "$OUT" | grep -oE '[0-9]+ 项全部通过')"
  ok "$(echo "$OUT" | grep -oE '转 [0-9]+° 变化 [0-9]+ BPM.*' | head -1)"
else
  bad "拖动逻辑测试失败"
fi

head_ "6.6 BPM 键盘输入"

OUT=$(python3 tools/test_bpm_input.py 2>&1)
if echo "$OUT" | grep -q "全部通过"; then
  ok "$(echo "$OUT" | grep -oE '[0-9]+ 项全部通过')"
else
  bad "输入逻辑测试失败"
  echo "$OUT" | grep "✗" | head -4 | sed 's/^/      /'
fi

head_ "6.7 屏幕适配"

OUT=$(python3 tools/test_layout_fit.py 2>&1)
if echo "$OUT" | grep -q "所有尺寸都放得下"; then
  ok "8 种屏幕尺寸都放得下（含极矮屏）"
else
  bad "布局在部分屏幕上溢出"
  echo "$OUT" | grep "✗" | head -4 | sed 's/^/      /'
fi

# ════════════════════════════════════════════════════════
head_ "7. 调音器未受影响"

CORE_OK=1
for m in "detectPitch" "getUserMedia" "strobeCanvas" "drawStrobe" \
         "playReference" "buildPianoKeys" "function theme()"; do
  if ! grep -q "$m" web/index.html; then
    bad "调音器功能丢失：$m"
    CORE_OK=0
  fi
done
[ "$CORE_OK" = "1" ] && ok "7 项核心功能全部保留"

# 原有行数
if [ -f /tmp/before_metro.html ]; then
  BEFORE_LINES=$(grep -c . /tmp/before_metro.html)
  LOST=0
  while IFS= read -r line; do
    [ -z "$line" ] && continue
    grep -qF "$line" web/index.html || LOST=$((LOST+1))
  done < <(grep . /tmp/before_metro.html)

  if [ "$LOST" -eq 0 ]; then
    ok "整合前的 $BEFORE_LINES 行全部保留"
  else
    bad "丢失 $LOST 行"
  fi
fi

# ════════════════════════════════════════════════════════
head_ "8. 幂等性（重复运行不累积）"

cp web/index.html /tmp/idem_check.html 2>/dev/null
SIZE_A=$(wc -c < web/index.html | tr -d ' ')

python3 tools/add_metronome.py >/dev/null 2>&1
python3 tools/add_metronome_js.py >/dev/null 2>&1

SIZE_B=$(wc -c < web/index.html | tr -d ' ')

if [ "$SIZE_A" = "$SIZE_B" ]; then
  ok "重复运行稳定（${SIZE_A} 字节不变）"
else
  bad "重复运行会累积：${SIZE_A} → ${SIZE_B}"
fi

# 关键元素没被重复插入
DUP=0
for m in "METRO-BLOCK:HEADER" "METRO-BLOCK:PAGES" "METRO-BLOCK:CSS" "METRONOME-JS-INSERTED"; do
  n=$(grep -c "$m" web/index.html 2>/dev/null || echo 0)
  # 起止标记各一次，所以 2 是正常值
  if [ "$n" -gt 2 ]; then
    bad "$m 出现 $n 次（应为 2）"
    DUP=1
  fi
done
[ "$DUP" -eq 0 ] && ok "所有标记都只出现一次（起+止）"

# ════════════════════════════════════════════════════════
echo
echo "${BOLD}════════════════════════════════════════════════${RESET}"
if [ "$fail" -eq 0 ]; then
  echo "${GREEN}${BOLD}✅ 全部通过（$pass 项）${RESET}"
else
  echo "${RED}${BOLD}✗ $fail 项失败，$pass 项通过${RESET}"
fi
echo "${BOLD}════════════════════════════════════════════════${RESET}"
echo
