#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  预览效果 —— 改完先看看，满意了再发布
#
#  这个工具做了特殊处理，保证你看到的一定是刚改完的最新样子，
#  不会被浏览器或 Service Worker 的缓存骗到。
# ══════════════════════════════════════════════════════════════

cd "$(dirname "$0")" 2>/dev/null || exit 1

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
CYAN=$'\033[36m'; DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

APP_DIR="$HOME/Desktop/始信调音器App"

clear
echo
echo "${BOLD}════════════════════════════════════════════════${RESET}"
echo "${BOLD}   预览效果${RESET}"
echo "${BOLD}════════════════════════════════════════════════${RESET}"
echo

if [ ! -d "$APP_DIR" ]; then
  echo "${RED}✗ 找不到项目文件夹${RESET}"
  printf "\n  按回车关闭 "
  read -r _ || true
  exit 1
fi

cd "$APP_DIR" || exit 1

# ── 同步离线版 ──
echo "${BOLD}同步文件…${RESET}"
if python3 tools/build_web.py --from-web > /tmp/preview_sync.log 2>&1; then
  echo "  ${GREEN}✓${RESET} 已同步到 App 离线版"
else
  echo "  ${YELLOW}!${RESET} 同步时有点问题（不影响预览）"
fi

# ── 显示当前配色，让用户确认改动在不在 ──
echo
echo "${BOLD}当前文件状态：${RESET}"
CUR=$(python3 -c "
import re
try:
    t = open('web/index.html', encoding='utf-8').read()
    m = re.search(r'--accent:\s*([^;]+);', t)
    print(m.group(1).strip() if m else '?')
except Exception:
    print('?')
" 2>/dev/null)
MOD=$(stat -f '%Sm' -t '%H:%M:%S' web/index.html 2>/dev/null)
echo "  ${DIM}文件名  web/index.html${RESET}"
echo "  ${DIM}改动时间 ${MOD}${RESET}"
echo "  ${DIM}当前主色 ${CUR}${RESET}"
echo

# ── 检查依赖 ──
if [ ! -f "tools/preview_server.py" ]; then
  echo "${RED}✗ 缺少预览服务器文件${RESET}"
  printf "\n  按回车关闭 "
  read -r _ || true
  exit 1
fi

# ── 先清掉可能残留的旧预览服务 ──
# 只针对「占用 8123 端口」且「命令行是 python http.server」的进程，
# 这几乎肯定是上次预览没关干净。不碰其它任何进程。
if command -v lsof >/dev/null 2>&1; then
  OLD=$(lsof -nP -iTCP:8123 -sTCP:LISTEN -t 2>/dev/null | head -1)
  if [ -n "$OLD" ]; then
    OLDCMD=$(ps -p "$OLD" -o command= 2>/dev/null)
    case "$OLDCMD" in
      *python*http.server*|*preview_server*)
        echo "  ${YELLOW}!${RESET} 上次的预览没关干净，正在关闭…"
        kill "$OLD" 2>/dev/null
        sleep 1
        echo "  ${GREEN}✓${RESET} 已清理"
        ;;
      *)
        echo "  ${YELLOW}!${RESET} 8123 端口被其它程序占用，将自动换个端口"
        ;;
    esac
  fi
fi

# ── 启动 ──
echo "${BOLD}启动预览服务器…${RESET}"
LOG="/tmp/preview_server.log"
: > "$LOG"

nohup python3 tools/preview_server.py 8123 > "$LOG" 2>&1 &
SERVER_PID=$!

sleep 2

if ! kill -0 "$SERVER_PID" 2>/dev/null; then
  echo "  ${RED}✗ 启动失败${RESET}"
  echo

  if grep -q "Address already in use" "$LOG" 2>/dev/null; then
    echo "  ${BOLD}原因：端口被占用${RESET}"
    echo "     ${DIM}可能上次的预览还开着。重启电脑或稍后再试。${RESET}"
  elif grep -q "PermissionError\|Operation not permitted" "$LOG" 2>/dev/null; then
    echo "  ${BOLD}原因：系统不允许启动本地服务${RESET}"
    echo "     ${DIM}可能是安全软件拦的。${RESET}"
  else
    echo "  ${BOLD}原因：${RESET}"
    grep -iE "error|denied|refused" "$LOG" 2>/dev/null | head -3 | sed 's/^/      /'
  fi

  echo
  echo "  ${BOLD}不碍事，改用直接打开文件的方式：${RESET}"
  echo "  ${DIM}能看到界面和样式，但麦克风用不了。${RESET}"
  echo
  open "$APP_DIR/web/index.html" 2>/dev/null \
    || echo "     手动打开：${DIM}$APP_DIR/web/index.html${RESET}"
  echo
  printf "  按回车关闭 "
  read -r _ || true
  exit 1
fi

# ── 从日志里读出实际端口 ──
PORT=$(grep -o 'http://127.0.0.1:[0-9]*' "$LOG" 2>/dev/null | head -1 | grep -o '[0-9]*$')
[ -z "$PORT" ] && PORT=8123

URL="http://127.0.0.1:${PORT}/"

echo "  ${GREEN}✓${RESET} 已启动"
echo
echo "${BOLD}════════════════════════════════════════════════${RESET}"
echo
echo "  预览地址：${CYAN}${URL}${RESET}"
echo
echo "  ${BOLD}${YELLOW}看到的是旧样子？在浏览器里按这个键强制刷新：${RESET}"
echo
echo "     ${BOLD}Command + Shift + R${RESET}"
echo
echo "  ${DIM}（或者按 Command + R 多刷新两次）${RESET}"
echo
echo "${BOLD}════════════════════════════════════════════════${RESET}"
echo

open "$URL" 2>/dev/null || echo "  ${DIM}（浏览器没自动打开，手动访问上面的地址）${RESET}"

echo
echo "  ${BOLD}满意就发布：${RESET}"
echo "    关掉这个窗口，双击「发布更新」"
echo
echo "  ${DIM}不满意就回去用「改界面」继续改，保存后刷新浏览器。${RESET}"
echo
echo "────────────────────────────────────────────────"
echo "  ${DIM}这个窗口关掉之前，预览一直可用。${RESET}"
echo

trap 'echo; echo "  预览已停止。"; exit 0' INT TERM
wait "$SERVER_PID" 2>/dev/null
