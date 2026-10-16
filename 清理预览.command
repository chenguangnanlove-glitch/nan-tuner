#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  清理预览 —— 把残留的预览服务全部关掉
#
#  什么时候用：
#    · 浏览器打开预览地址，看到的是「文件列表」而不是调音器
#    · 提示端口被占用
#    · 不确定有没有旧服务在后台跑
# ══════════════════════════════════════════════════════════════

cd "$(dirname "$0")" 2>/dev/null || exit 1

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

clear
echo
echo "${BOLD}════════════════════════════════════════════════${RESET}"
echo "${BOLD}   清理预览服务${RESET}"
echo "${BOLD}════════════════════════════════════════════════${RESET}"
echo

FOUND=0
KILLED=0
OTHER_OCCUPIED=0
LIKELY_OURS=0

# ── 先按 PID 文件清理 ──
PIDFILE="/tmp/shixin-preview.pid"
if [ -f "$PIDFILE" ]; then
  PID=$(cat "$PIDFILE" 2>/dev/null | tr -d ' \n')
  if [ -n "$PID" ] && kill -0 "$PID" 2>/dev/null; then
    CMD=$(ps -p "$PID" -o command= 2>/dev/null)
    if echo "$CMD" | grep -q "preview_server"; then
      FOUND=$((FOUND + 1))
      echo "  发现预览服务（PID ${PID}）"
      kill "$PID" 2>/dev/null && sleep 0.5 && kill -9 "$PID" 2>/dev/null
      KILLED=$((KILLED + 1))
      echo "  ${GREEN}✓${RESET} 已关闭"
    fi
  fi
  rm -f "$PIDFILE"
fi

# ── 再扫端口 ──
echo
echo "  检查 8123–8183 端口…"
echo

for PORT in $(seq 8123 8183); do
  PIDS=$(lsof -nP -iTCP:$PORT -sTCP:LISTEN -t 2>/dev/null)

  for PID in $PIDS; do
    [ -z "$PID" ] && continue

    CMD=$(ps -p "$PID" -o command= 2>/dev/null)
    CWD=$(lsof -p "$PID" -a -d cwd 2>/dev/null | tail -1 | awk '{print $NF}')

    # 只处理确实是本地预览服务的进程
    case "$CMD" in
      *preview_server*)
        IS_OURS=1          # 我们自己写的预览服务
        ;;
      *http.server*|*SimpleHTTP*)
        # 普通的 http.server：只当它的目录在项目里才认为是预览残留
        case "$CWD" in
          *始信调音器App*) IS_OURS=1 ;;
          *)               IS_OURS=0 ;;
        esac
        ;;
      *)
        IS_OURS=0
        ;;
    esac

    if [ "$IS_OURS" = "1" ]; then
      FOUND=$((FOUND + 1))
      echo "  端口 ${PORT}：PID ${PID}"
      echo "    ${DIM}命令：$(echo "$CMD" | cut -c1-64)${RESET}"
      [ -n "$CWD" ] && echo "    ${DIM}目录：$(echo "$CWD" | sed "s|$HOME|~|")${RESET}"

      kill "$PID" 2>/dev/null
      sleep 0.4
      if kill -0 "$PID" 2>/dev/null; then
        kill -9 "$PID" 2>/dev/null
        sleep 0.3
      fi

      if kill -0 "$PID" 2>/dev/null; then
        echo "    ${RED}✗ 关不掉（可能需要管理员权限）${RESET}"
      else
        KILLED=$((KILLED + 1))
        echo "    ${GREEN}✓ 已关闭${RESET}"
      fi
      echo
    elif [ -n "$PIDS" ]; then
      # 端口被占，但不像是我们的服务
      OTHER_OCCUPIED=1
      echo "  ${YELLOW}!${RESET} 端口 ${PORT} 被占用（不像是预览服务，不动它）"
      echo "    PID ${PID}"
      if [ -n "$CMD" ]; then
        echo "    ${DIM}命令：$(echo "$CMD" | cut -c1-64)${RESET}"
      else
        echo "    ${DIM}（查不到进程信息）${RESET}"
      fi
      [ -n "$CWD" ] && echo "    ${DIM}目录：$(echo "$CWD" | sed "s|$HOME|~|")${RESET}"

      # 如果目录就是我们的项目，那多半是预览残留，只是识别不出命令
      case "$CWD" in
        *始信调音器App*)
          echo "    ${YELLOW}→ 目录看起来是本项目，可能是预览残留${RESET}"
          echo "    ${DIM}   仍要清理的话，在「活动监视器」里结束 PID ${PID}${RESET}"
          LIKELY_OURS=$((LIKELY_OURS + 1))
          ;;
      esac
      echo
    fi
  done
done

# ── 结果 ──
echo "────────────────────────────────────────────────"
echo

if [ "$FOUND" -eq 0 ] && [ "$LIKELY_OURS" -gt 0 ]; then
  echo "  ${YELLOW}有 ${LIKELY_OURS} 个疑似预览残留，但识别不出具体命令${RESET}"
  echo
  echo "  ${BOLD}手动清理：${RESET}"
  echo "    1. 打开「活动监视器」（在启动台里搜）"
  echo "    2. 在搜索框输入 python3"
  echo "    3. 找到占用端口 8123 的那个，选中后点左上角的 ✕ 结束"
  echo
  echo "  ${DIM}或者重启电脑 —— 最简单也最彻底。${RESET}"
elif [ "$FOUND" -eq 0 ]; then
  echo "  ${GREEN}没有发现残留的预览服务${RESET}"
  echo
  echo "  如果浏览器还是显示旧内容，试试："
  echo "    ${BOLD}1. 关掉那个浏览器标签页，重新打开${RESET}"
  echo "    ${BOLD}2. 或者在浏览器里按 Command + Shift + R${RESET}"
elif [ "$KILLED" -eq "$FOUND" ]; then
  echo "  ${GREEN}${BOLD}✓ 已清理 ${KILLED} 个预览服务${RESET}"
  echo
  echo "  现在可以双击「预览效果」重新启动了。"
else
  echo "  ${YELLOW}发现 ${FOUND} 个，关掉了 ${KILLED} 个${RESET}"
  echo
  echo "  还有关不掉的，说明它们属于别的程序或需要管理员权限。"
  echo
  echo "  ${BOLD}手动清理办法：${RESET}"
  echo "    1. 打开「活动监视器」（在启动台里搜）"
  echo "    2. 在搜索框输入 python"
  echo "    3. 找到「Python」进程，看它的信息里有 http.server 或 preview_server"
  echo "    4. 选中，点左上角的 ✕ 结束它"
fi

echo
printf "  按回车关闭这个窗口 "
read -r _ || true
