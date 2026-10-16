#!/bin/bash
# ==============================================================================
#  查看你的 GitHub 仓库里现在有什么
#
#  只读操作：克隆一份到临时目录看看，不改动任何东西，不会推送。
#
#  用法：
#    bash tools/inspect_repo.sh https://github.com/你的用户名/nan-tuner.git
#
#  结果会：
#    1. 打印在屏幕上
#    2. 同时保存到 tools/repo-report.txt（方便发给别人看）
# ==============================================================================

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"
REPORT="$HERE/repo-report.txt"

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

ok()   { echo "  ${GREEN}✓${RESET} $*"; }
warn() { echo "  ${YELLOW}!${RESET} $*"; }
err()  { echo "  ${RED}✗${RESET} $*"; }
step() { echo; echo "${BOLD}$*${RESET}"; }

# 报告写入文件时去掉颜色码。
# 注意：必须用 sed，不能用 bash 的 ${var//pat/repl}——
# bash glob 里的 * 匹配任意字符且贪婪，会把中间的文字一起吃掉。
# sed 的 [0-9;]* 只重复字符类，不会越界。
# 另外 macOS 的 sed 不认 \x1b，要把 ESC 字符直接嵌进表达式。
ESC_CHAR=$'\033'
both() {
  echo "$*"
  printf '%s\n' "$*" | sed "s/${ESC_CHAR}\[[0-9;]*m//g" >> "$REPORT"
}

: > "$REPORT"

echo
echo "${BOLD}检查 GitHub 仓库现状${RESET}"
echo "${DIM}（只读操作，不会改动任何东西）${RESET}"
echo

# ════════════════════════════════════════════════════════════
step "1. 仓库地址"

REPO="${1:-}"
if [ -z "$REPO" ]; then
  echo "  ${DIM}格式：https://github.com/用户名/仓库名.git${RESET}"
  echo
  printf "  仓库地址 > "
  read -r REPO
fi

if [ -z "$REPO" ]; then
  err "没给地址。用法：bash tools/inspect_repo.sh <仓库地址>"
  exit 1
fi

# 本地目录（用于自己测试）：直接用，不规范化成 GitHub 地址
if [ -d "$REPO" ]; then
  REPO="$(cd "$REPO" && pwd)"
else
  case "$REPO" in
    git@*)              : ;;
    https://*|http://*) REPO="${REPO%.git}.git" ;;
    github.com/*)       REPO="https://${REPO%.git}.git" ;;
    *)                  REPO="https://github.com/${REPO#/}"; REPO="${REPO%.git}.git" ;;
  esac
fi

both "仓库地址：$REPO"
both "检查时间：$(date '+%Y-%m-%d %H:%M:%S')"

# ════════════════════════════════════════════════════════════
step "2. 网络连接"

detect_sys_proxy() {
  local ph pp
  ph=$(scutil --proxy 2>/dev/null | awk '/HTTPProxy/ {print $3; exit}')
  pp=$(scutil --proxy 2>/dev/null | awk '/HTTPPort/  {print $3; exit}')
  if [ -n "$ph" ] && [ -n "$pp" ] && [ "$ph" != "0.0.0.0" ]; then
    echo "$ph:$pp"
  fi
}

PROXY_ADDR="$(detect_sys_proxy)"
GIT_PROXY_OPT=""

try_connect() {
  # 本地目录不用测网络
  if [ -d "$REPO" ]; then
    echo "200"
    return
  fi
  if [ -n "$1" ]; then
    curl -x "http://$1" -s -o /dev/null -w '%{http_code}' --max-time 8 "$REPO" 2>/dev/null
  else
    curl --noproxy '*' -s -o /dev/null -w '%{http_code}' --max-time 8 "$REPO" 2>/dev/null
  fi
}

DIRECT="$(try_connect '')"
if [ "$DIRECT" = "200" ] || [ "$DIRECT" = "301" ] || [ "$DIRECT" = "302" ]; then
  ok "直连可用"
else
  if [ -n "$PROXY_ADDR" ]; then
    PROXY_RESULT="$(try_connect "$PROXY_ADDR")"
    if [ "$PROXY_RESULT" = "200" ] || [ "$PROXY_RESULT" = "301" ] || [ "$PROXY_RESULT" = "302" ]; then
      ok "通过代理可用（${PROXY_ADDR}）"
      GIT_PROXY_OPT="-c http.proxy=http://$PROXY_ADDR"
    else
      err "代理也连不上（${PROXY_ADDR}）—— Clash 开着吗？"
      exit 1
    fi
  else
    err "直连不通，也没检测到代理"
    exit 1
  fi
fi

# ════════════════════════════════════════════════════════════
step "3. 拉取仓库内容"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP" 2>/dev/null || true' EXIT
CLONE="$TMP/repo"

echo "  ${DIM}正在克隆（只拉最新一次提交，很快）…${RESET}"

if ! git $GIT_PROXY_OPT clone --depth=1 --quiet "$REPO" "$CLONE" 2>"$TMP/err"; then
  err "克隆失败"
  echo
  head -5 "$TMP/err" | sed 's/^/    /'
  echo
  echo "  ${DIM}可能是：仓库地址写错、需要登录、或者仓库是私有的（私有仓库要输 token）${RESET}"
  rm -rf "$TMP"
  exit 1
fi
ok "克隆成功"

cd "$CLONE"

BRANCH="$(git rev-parse --abbrev-ref HEAD)"
COMMIT="$(git log -1 --format='%h  %s  (%ad)' --date=short)"
FILE_COUNT="$(git ls-files | wc -l | tr -d ' ')"
SIZE="$(du -sh . 2>/dev/null | cut -f1)"

both ""
both "分支：$BRANCH"
both "最新提交：$COMMIT"
both "文件数：$FILE_COUNT"
both "占用：$SIZE"

# ════════════════════════════════════════════════════════════
step "4. 文件结构"

both ""
both "─── 全部文件 ───"
git ls-files | head -80 | while read -r f; do
  both "  $f"
done
TOTAL="$(git ls-files | wc -l | tr -d ' ')"
if [ "$TOTAL" -gt 80 ]; then
  both "  …（还有 $((TOTAL - 80)) 个文件未显示）"
fi

# ════════════════════════════════════════════════════════════
step "5. 分析"

both ""
both "─── 分析结果 ───"

HAS_INDEX=0; HAS_TUNER=0; HAS_NETLIFY=0; HAS_PKG=0
TOP_DIRS=""

[ -f index.html ] && HAS_INDEX=1
[ -f netlify.toml ] && HAS_NETLIFY=1
[ -f package.json ] && HAS_PKG=1

if [ "$HAS_INDEX" -eq 1 ]; then
  if grep -q -l "getUserMedia\|detectPitch\|调音" index.html 2>/dev/null; then
    HAS_TUNER=1
  fi
fi

# 顶层目录
TOP_DIRS="$(git ls-files | awk -F/ 'NF>1 {print $1}' | sort -u | head -20)"

if [ "$HAS_INDEX" -eq 1 ]; then
  both "  ✓ 根目录有 index.html —— 这是个网页项目"
else
  both "  · 根目录没有 index.html"
fi

if [ "$HAS_TUNER" -eq 1 ]; then
  both "  ✓ 那个 index.html 就是你的调音器"
fi

if [ "$HAS_NETLIFY" -eq 1 ]; then
  both "  ✓ 有 netlify.toml"
  PUB="$(grep -E '^\s*publish' netlify.toml 2>/dev/null | head -1 | sed 's/.*= *//; s/"//g')"
  [ -n "$PUB" ] && both "    → Netlify 发布目录：$PUB" || both "    → 没写 publish（默认发布根目录）"
fi

if [ "$HAS_PKG" -eq 1 ]; then
  both "  ! 有 package.json —— 可能用了前端框架，需要构建"
fi

if [ -n "$TOP_DIRS" ]; then
  both "  顶层目录："
  echo "$TOP_DIRS" | while read -r d; do
    both "    $d/"
  done
fi

# ════════════════════════════════════════════════════════════
step "6. 结论"

both ""
if [ "$HAS_TUNER" -eq 1 ] && [ "$HAS_PKG" -eq 0 ]; then
  both "  ${GREEN}情况：纯静态网页仓库，根目录就是你的调音器${RESET}"
  both ""
  both "  合并方案很简单："
  both "    1. 你现有的 index.html 会被新版替换（新版功能完全一样，"
  both "       只是多了 PWA 支持和「下载 App」入口）"
  both "    2. 新增 manifest.webmanifest、sw.js、icons/、download/"
  both "    3. 新增 android/ 工程和 .github/ 流水线"
  both "    4. Netlify 发布目录填 . （根目录）"
  both ""
  both "  风险：低。原文件会先备份。"
elif [ "$HAS_PKG" -eq 1 ]; then
  both "  ${YELLOW}情况：这个仓库带构建流程（package.json）${RESET}"
  both ""
  both "  不能直接覆盖，需要先弄清楚构建方式。"
  both "  请把上面「顶层目录」和 package.json 的内容告诉我。"
else
  both "  ${YELLOW}情况：需要人工判断${RESET}"
  both ""
  both "  请把上面的完整输出发给我，我来定方案。"
fi

both ""
both "─── 报告结束 ───"

# ════════════════════════════════════════════════════════════
echo
echo "════════════════════════════════════════════════════════════"
echo "${GREEN}${BOLD}检查完成${RESET}"
echo
echo "  完整报告已保存到："
echo "  ${BOLD}tools/repo-report.txt${RESET}"
echo
echo "  ${DIM}告诉我「看完了」就行，我能直接读这个文件。${RESET}"
echo "════════════════════════════════════════════════════════════"

echo
 echo "${DIM}（临时克隆已清理）${RESET}"
