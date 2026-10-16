#!/bin/bash
# ══════════════════════════════════════════════════════════════
#  发布更新 —— 把你改的内容推到线上
#
#  双击运行。它会：
#    1. 同步 App 内置的离线版
#    2. 检查有没有实际改动
#    3. 推到 GitHub
#    4. Netlify 自动发布，手机上立即生效
#
#  前提：改的是 web/ 里的文件（主要是 web/index.html）
# ══════════════════════════════════════════════════════════════

cd "$(dirname "$0")" 2>/dev/null || exit 1

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
CYAN=$'\033[36m'; DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

APP_DIR="$HOME/Desktop/始信调音器App"

clear
echo
echo "${BOLD}════════════════════════════════════════════════${RESET}"
echo "${BOLD}   发布更新${RESET}"
echo "${BOLD}════════════════════════════════════════════════${RESET}"
echo

if [ ! -d "$APP_DIR" ]; then
  echo "${RED}✗ 找不到项目文件夹${RESET}"
  printf "\n  按回车关闭 "
  read -r _ || true
  exit 1
fi

cd "$APP_DIR" || exit 1

# ════════════════════════════════════════════════════════
echo "${BOLD}第 1 步 / 共 3 步：同步 App 离线版${RESET}"
echo

if python3 tools/build_web.py --from-web > /tmp/publish_build.log 2>&1; then
  grep -E "✅|→" /tmp/publish_build.log | sed 's/^/  /' | head -5
  echo "  ${GREEN}✓${RESET} 手机 App 内置的版本也更新了"
else
  echo "  ${YELLOW}!${RESET} 同步遇到问题："
  tail -5 /tmp/publish_build.log | sed 's/^/      /'
  echo
  printf "  还要继续发布吗？(y 继续 / 其它键取消) "
  read -r ANS
  if [ "$ANS" != "y" ]; then
    echo "  已取消。"
    printf "\n  按回车关闭 "
    read -r _ || true
    exit 1
  fi
fi
echo

# ════════════════════════════════════════════════════════
echo "${BOLD}第 2 步 / 共 3 步：这次改了什么？${RESET}"
echo
echo "  ${DIM}写一句话说明，会记录在更新历史里。${RESET}"
echo "  ${DIM}直接按回车就用默认说明。${RESET}"
echo
printf "  > "
read -r DESC
[ -z "$DESC" ] && DESC="更新网页内容"
echo

# ════════════════════════════════════════════════════════
echo "${BOLD}第 3 步 / 共 3 步：上传${RESET}"
echo

export SHIXIN_COMMIT_MSG="$DESC"
export SHIXIN_QUIET=1

bash tools/deploy.sh 2>&1 | tee /tmp/publish_out.log | \
  grep -E "✓|✗|原因|接下来|https://" | head -25

RC=${PIPESTATUS[0]}

echo
if [ "$RC" -eq 0 ]; then
  echo "${GREEN}${BOLD}════════════════════════════════════════════════${RESET}"
  echo "${GREEN}${BOLD}   ✅ 发布成功${RESET}"
  echo "${GREEN}${BOLD}════════════════════════════════════════════════${RESET}"
  echo
  echo "  ${BOLD}现在：${RESET}"
  echo "    1. Netlify 会在 30 秒左右自动发布"
  echo "    2. 手机上打开 App（或网页）就是新版了"
  echo "    3. ${DIM}不用重新安装 App${RESET}"
  echo
  echo "  ${DIM}想确认效果？等半分钟后打开 https://nan-tuner.cc${RESET}"
  echo
else
  echo "${RED}${BOLD}✗ 发布失败${RESET}"
  echo
  if [ -f /tmp/publish_out.log ]; then
    grep -A 3 "原因" /tmp/publish_out.log | head -10 | sed 's/^/  /'
  fi
  echo
  echo "  ${DIM}完整记录：/tmp/publish_out.log${RESET}"
  echo "  ${DIM}搞不定就双击「② 诊断问题」${RESET}"
  echo
fi

printf "  按回车关闭这个窗口 "
read -r _ || true
