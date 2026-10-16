#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  改界面 —— 换配色、改文字，点几下就行，不用碰代码
# ══════════════════════════════════════════════════════════════

cd "$(dirname "$0")" 2>/dev/null || exit 1

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

APP_DIR="$HOME/Desktop/始信调音器App"

# ── 定位工具 ──
if [ -f "$APP_DIR/tools/ui_tool.py" ]; then
  TOOL="$APP_DIR/tools/ui_tool.py"
elif [ -f "./tools/ui_tool.py" ]; then
  TOOL="$(pwd)/tools/ui_tool.py"
else
  osascript -e 'display alert "找不到项目文件" message "请确认「始信调音器App」文件夹还在桌面上。" as critical' 2>/dev/null
  echo "找不到项目文件"
  exit 1
fi

# ── 检查依赖 ──
if ! command -v python3 >/dev/null 2>&1; then
  osascript -e 'display alert "找不到 Python" message "这台电脑上没装 Python 3。" as critical' 2>/dev/null
  exit 1
fi

if ! python3 -c "import tkinter" 2>/dev/null; then
  osascript -e 'display alert "缺少界面组件" message "需要先安装 tkinter。\n\n在「终端」里运行：\nbrew install python-tk" as warning' 2>/dev/null
  exit 1
fi

# ── 后台启动 ──
LOG="/tmp/ui_tool.log"
: > "$LOG"

nohup python3 "$TOOL" > "$LOG" 2>&1 &
TOOL_PID=$!

sleep 1.5

if ! kill -0 "$TOOL_PID" 2>/dev/null; then
  echo
  echo "${RED}${BOLD}界面没能启动${RESET}"
  echo
  if [ -s "$LOG" ]; then
    echo "  错误信息："
    tail -10 "$LOG" | sed 's/^/    /'
  fi
  echo
  echo "${DIM}  完整日志：$LOG${RESET}"
  echo
  printf "  按回车关闭 "
  read -r _ || true
  exit 1
fi

echo
echo "${GREEN}${BOLD}✓ 「改界面」已打开${RESET}"
echo
echo "  在屏幕上找到那个窗口，可以："
echo "    ${BOLD}配色${RESET} 标签页 —— 点选喜欢的配色"
echo "    ${BOLD}文字${RESET} 标签页 —— 改名字、按钮上的字"
echo
echo "  改完点「保存」，然后双击「预览效果」看真实效果。"
echo
echo "${DIM}  这个终端窗口可以直接关掉。${RESET}"
echo
