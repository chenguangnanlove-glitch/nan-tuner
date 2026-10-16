#!/bin/bash
# 从干净状态重新整合节拍器，并完整验证

set -uo pipefail

cd "/Users/nan/Desktop/始信调音器App" || exit 1

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

echo
echo "${BOLD}════════ 重新整合节拍器 ════════${RESET}"
echo

# ── 1. 回到干净状态 ──
echo "${BOLD}[1/6]${RESET} 恢复原始文件"
if [ ! -f /tmp/before_metro.html ]; then
  echo "  ${RED}✗ 找不到原始备份${RESET}"
  exit 1
fi
cp /tmp/before_metro.html web/index.html
echo "  ${GREEN}✓${RESET} 已恢复（$(wc -c < web/index.html | tr -d ' ') 字节）"
echo

# ── 2. 插入 HTML ──
echo "${BOLD}[2/6]${RESET} 插入 HTML 结构"
OUT=$(python3 tools/add_metronome.py 2>&1)
if echo "$OUT" | grep -q "✓"; then
  echo "  ${GREEN}✓${RESET} 完成"
else
  echo "  ${RED}✗ 失败${RESET}"
  echo "$OUT" | sed 's/^/      /'
  exit 1
fi
echo

# ── 3. 插入 JS ──
echo "${BOLD}[3/6]${RESET} 插入 JS"
OUT=$(python3 tools/add_metronome_js.py 2>&1)
if echo "$OUT" | grep -q "✓"; then
  echo "$OUT" | grep -E "核心逻辑|音频引擎|界面控制|合计" | sed 's/^/  /'
else
  echo "  ${RED}✗ 失败${RESET}"
  echo "$OUT" | sed 's/^/      /'
  exit 1
fi
echo

# ── 4. 结构验证 ──
echo "${BOLD}[4/6]${RESET} HTML 结构"
OUT=$(python3 tools/_verify_structure.py 2>&1)
if echo "$OUT" | grep -q "结构完整"; then
  echo "  ${GREEN}✓${RESET} 标签配对、元素齐全、原有内容完整"
else
  echo "  ${RED}✗ 有问题${RESET}"
  echo "$OUT" | tail -12 | sed 's/^/      /'
  exit 1
fi
echo

# ── 5. JS 语法 ──
echo "${BOLD}[5/6]${RESET} JS 语法"
OUT=$(bash tools/_check_js.sh 2>&1)
if echo "$OUT" | grep -q "✗"; then
  echo "  ${RED}✗ 有语法错误${RESET}"
  echo "$OUT" | grep -A 2 "✗" | sed 's/^/      /'
  exit 1
else
  echo "$OUT" | grep -E "第 [0-9]+ 块" | sed 's/^/  /'
fi
echo

# ── 6. 逻辑运行 ──
echo "${BOLD}[6/6]${RESET} 核心逻辑实际运行"
OUT=$(python3 tools/_run_metro_test.py 2>&1)
if echo "$OUT" | grep -q "全部通过"; then
  echo "$OUT" | grep -oE "[0-9]+ 项全部通过.*" | sed 's/^/  /'
else
  echo "  ${RED}✗ 测试失败${RESET}"
  echo "$OUT" | tail -10 | sed 's/^/      /'
  exit 1
fi
echo

# ── id 交叉检查 ──
echo "${BOLD}[附]${RESET} 元素 id 交叉引用"
OUT=$(python3 tools/_check_ids.py 2>&1)
if echo "$OUT" | grep -q "全部被引用的 id 都已定义\|所有被引用的 id 都已定义"; then
  echo "  ${GREEN}✓${RESET} JS 引用的 id 全部存在"
else
  echo "  ${YELLOW}!${RESET} 检查结果："
  echo "$OUT" | grep -E "✗" | head -5 | sed 's/^/      /'
fi
echo

echo "${GREEN}${BOLD}════════ 整合完成 ════════${RESET}"
echo
echo "  文件大小：$(wc -c < web/index.html | tr -d ' ') 字节"
echo
echo "  ${BOLD}下一步：同步离线版${RESET}"
echo "    python3 tools/build_web.py --from-web"
echo
