#!/bin/bash
# ==============================================================================
#  一键推送到 GitHub
#
#  用法：
#    bash tools/push.sh https://github.com/你的用户名/shixin-tuner.git
#
#  脚本会自动处理：
#    - git 身份没配置（新手最常见的报错）
#    - 仓库没初始化 / 分支名不对
#    - 远程地址已存在 / 写错了
#    - 推送时漏掉文件
# ==============================================================================

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

ok()   { echo "  ${GREEN}✓${RESET} $*"; }
warn() { echo "  ${YELLOW}!${RESET} $*"; }
err()  { echo "  ${RED}✗${RESET} $*"; }
step() { echo; echo "${BOLD}$*${RESET}"; }

cd "$ROOT"

echo
echo "${BOLD}始信音乐 · 调音器 —— 推送到 GitHub${RESET}"

# ════════════════════════════════════════════════════════════
step "1. 检查环境"

command -v git >/dev/null 2>&1 || { err "没找到 git，请先安装 Xcode 命令行工具"; exit 1; }
ok "git $(git --version | awk '{print $3}')"

# ════════════════════════════════════════════════════════════
step "2. 检查 git 身份"

NEED_IDENTITY=0
GIT_NAME="$(git config --global user.name 2>/dev/null || true)"
GIT_MAIL="$(git config --global user.email 2>/dev/null || true)"

if [ -z "$GIT_NAME" ]; then
  NEED_IDENTITY=1
  warn "还没设置名字（GitHub 提交记录里会显示这个）"
else
  ok "名字：$GIT_NAME"
fi

if [ -z "$GIT_MAIL" ]; then
  NEED_IDENTITY=1
  warn "还没设置邮箱"
else
  ok "邮箱：$GIT_MAIL"
fi

if [ "$NEED_IDENTITY" -eq 1 ]; then
  echo
  echo "  ${DIM}GitHub 需要知道是谁提交的。建议用你 GitHub 账号的邮箱。${RESET}"
  echo "  ${DIM}（在 GitHub 的 Settings → Emails 里能看到）${RESET}"
  echo

  if [ -z "$GIT_NAME" ]; then
    printf "  你的名字 > "
    read -r INPUT_NAME
    if [ -n "$INPUT_NAME" ]; then
      git config --global user.name "$INPUT_NAME"
      ok "名字已设为：$INPUT_NAME"
    else
      err "名字不能为空"
      exit 1
    fi
  fi

  if [ -z "$GIT_MAIL" ]; then
    printf "  你的邮箱 > "
    read -r INPUT_MAIL
    if [ -n "$INPUT_MAIL" ]; then
      git config --global user.email "$INPUT_MAIL"
      ok "邮箱已设为：$INPUT_MAIL"
    else
      err "邮箱不能为空"
      exit 1
    fi
  fi
fi

# ════════════════════════════════════════════════════════════
step "3. 检查网络能不能连上 GitHub"

detect_sys_proxy() {
  local ph pp
  ph=$(scutil --proxy 2>/dev/null | awk '/HTTPProxy/ {print $3; exit}')
  pp=$(scutil --proxy 2>/dev/null | awk '/HTTPPort/  {print $3; exit}')
  if [ -n "$ph" ] && [ -n "$pp" ] && [ "$ph" != "0.0.0.0" ]; then
    echo "$ph:$pp"
  fi
}

try_url() {
  # $1 = 代理地址（可空），$2 = 超时
  if [ -n "$1" ]; then
    curl -x "http://$1" -s -o /dev/null -w '%{http_code}' --max-time "$2" https://github.com 2>/dev/null
  else
    curl --noproxy '*' -s -o /dev/null -w '%{http_code}' --max-time "$2" https://github.com 2>/dev/null
  fi
}

HTTP_PROXY_ADDR="$(detect_sys_proxy)"
WORKING_PROXY=""

echo "  ${DIM}测试直连 GitHub…${RESET}"
DIRECT_CODE="$(try_url '' 8)"

if [ "$DIRECT_CODE" = "200" ] || [ "$DIRECT_CODE" = "301" ] || [ "$DIRECT_CODE" = "302" ]; then
  ok "直连可用（HTTP ${DIRECT_CODE}）"
  # 清掉可能残留的 git 代理，避免 Clash 没开时反而连不上
  if git config --global --get http.https://github.com.proxy >/dev/null 2>&1; then
    git config --global --unset http.https://github.com.proxy
    ok "已清除之前设置的 git 代理（直连能通，不需要代理）"
  fi
else
  warn "直连不通（HTTP ${DIRECT_CODE:-超时}）"

  if [ -n "$HTTP_PROXY_ADDR" ]; then
    echo "  ${DIM}检测到系统代理 ${HTTP_PROXY_ADDR}，测试中…${RESET}"
    PROXY_CODE="$(try_url "$HTTP_PROXY_ADDR" 8)"
    if [ "$PROXY_CODE" = "200" ] || [ "$PROXY_CODE" = "301" ] || [ "$PROXY_CODE" = "302" ]; then
      ok "代理可用（HTTP ${PROXY_CODE}）"
      WORKING_PROXY="$HTTP_PROXY_ADDR"
    else
      err "代理连不上（HTTP ${PROXY_CODE:-超时}）"
      echo "  ${DIM}很可能 Clash Verge 没启动。请先打开它，再重新运行本脚本。${RESET}"
    fi
  else
    err "没有检测到系统代理"
    echo "  ${DIM}如果你在用 Clash 之类的工具，先把它打开。${RESET}"
  fi

  if [ -z "$WORKING_PROXY" ]; then
    echo
    echo "${BOLD}现在有两条路：${RESET}"
    echo "  1. 打开 Clash Verge（或其它代理），然后重新运行本脚本"
    echo "  2. 如果你确定能连上 GitHub（比如公司网络），输 y 强行继续"
    echo
    printf "  强行继续？(y/n) > "
    read -r FORCE_CONTINUE
    if [ "$FORCE_CONTINUE" != "y" ]; then
      echo
      echo "  ${DIM}已取消。打开代理后再跑：${RESET}"
      echo "  ${DIM}bash tools/push.sh${RESET}"
      exit 1
    fi
  fi
fi

# 给 git 配上测试通过的代理（只作用于 GitHub，不影响其他仓库）
if [ -n "$WORKING_PROXY" ]; then
  git config --global http.https://github.com.proxy "http://$WORKING_PROXY"
  git config --global https.https://github.com.proxy "http://$WORKING_PROXY"
  ok "已让 git 通过代理访问 GitHub（仅 GitHub，不影响其它）"
  echo "  ${DIM}以后想取消：git config --global --unset http.https://github.com.proxy${RESET}"
fi

# ════════════════════════════════════════════════════════════
step "4. 确认仓库地址"

REPO="${1:-}"

if [ -z "$REPO" ]; then
  echo "  ${DIM}格式：https://github.com/用户名/仓库名.git${RESET}"
  echo "  ${DIM}还没建仓库？先去 https://github.com/new 建一个，${RESET}"
  echo "  ${DIM}名字随便起（例如 shixin-tuner），不要勾选任何初始化选项。${RESET}"
  echo
  printf "  仓库地址 > "
  read -r REPO
fi

if [ -z "$REPO" ]; then
  err "仓库地址不能为空。用法：bash tools/push.sh <仓库地址>"
  exit 1
fi

# 容错：允许省略 .git 后缀，允许写成 git@... / github.com/... / 用户名/仓库名
case "$REPO" in
  git@*)                    : ;;
  https://*|http://*)       REPO="${REPO%.git}.git" ;;
  github.com/*)             REPO="https://${REPO%.git}.git" ;;
  *)                        REPO="https://github.com/${REPO#/}"; REPO="${REPO%.git}.git" ;;
esac

echo "  目标：$REPO"

# ════════════════════════════════════════════════════════════
step "5. 整理提交"

if [ ! -d .git ]; then
  git init -q
  ok "已初始化仓库"
else
  ok "仓库已存在"
fi

git branch -M main 2>/dev/null && ok "分支：main"

# 远程地址
if git remote get-url origin >/dev/null 2>&1; then
  OLD="$(git remote get-url origin)"
  if [ "$OLD" != "$REPO" ]; then
    git remote set-url origin "$REPO"
    ok "远程地址已更新（原来是 ${OLD}）"
  else
    ok "远程地址已正确"
  fi
else
  git remote add origin "$REPO"
  ok "已设置远程地址"
fi

# 安全检查：确认密钥没被纳入
if [ -d tools/keystore ]; then
  LEAK="$(git ls-files --others --exclude-standard | grep -c 'keystore/' || true)"
  if [ "$LEAK" != "0" ]; then
    err "危险：签名密钥可能被提交！"
    echo "  ${DIM}请检查 .gitignore 是否包含 tools/keystore/${RESET}"
    exit 1
  fi
  ok "签名密钥已排除（不会被上传）"
fi

# 暂存
git add -A
COUNT="$(git diff --staged --name-only | wc -l | tr -d ' ')"
ok "已暂存 $COUNT 个文件"

if [ "$COUNT" = "0" ]; then
  warn "没有新变化需要提交"
else
  git commit -q -m "始信音乐调音器：安卓 App 工程 + PWA 网页版

- 安卓 WebView 外壳，含麦克风授权、离线兜底、版本更新提示
- PWA 网页版，支持添加到主屏幕与离线使用
- 下载页与自动构建流水线
- 站点地址：https://nan-tuner.cc"
  ok "已提交"
fi

# ════════════════════════════════════════════════════════════
step "6. 推送到 GitHub"

echo "  ${DIM}如果弹出用户名/密码，密码处请粘贴 Personal Access Token${RESET}"
echo "  ${DIM}（GitHub 从 2021 年起不接受账号密码了）${RESET}"
echo "  ${DIM}还没生成过？https://github.com/settings/tokens 选 classic，勾 repo 权限${RESET}"
echo

PUSH_LOG="$(mktemp)"
git push -u origin main > "$PUSH_LOG" 2>&1
PUSH_STATUS=$?
cat "$PUSH_LOG"

if [ $PUSH_STATUS -eq 0 ]; then
  rm -f "$PUSH_LOG"
  echo
  echo "${GREEN}${BOLD}✅ 推送成功${RESET}"
  echo
  echo "  仓库地址：$REPO"
  echo
  echo "${BOLD}接下来：${RESET}"
  echo "  1. 去仓库的 Settings → Secrets and variables → Actions"
  echo "     添加 4 个密钥（内容见 tools/keystore/密钥信息.txt）"
  echo "       KEYSTORE_BASE64"
  echo "       KEYSTORE_PASSWORD"
  echo "       KEY_PASSWORD"
  echo "       KEY_ALIAS"
  echo
  echo "  2. 去仓库的 Actions 标签 → 构建安卓 APK → Run workflow"
  echo "     等几分钟，APK 就自动打包好了"
  echo
  echo "  3. 去 Netlify 把你的站点连到这个仓库，发布目录填 web"
  echo
  echo "  之后手机上打开 https://nan-tuner.cc 就能下载安装了。"
  echo
  exit 0
fi

# ---------- 推送失败：分辨原因，给出对症的办法 ----------
rm -f "$PUSH_LOG"
echo
err "推送失败"
echo

# 先确认远程到底能不能连上
REMOTE_OUT="$(git ls-remote --heads origin 2>&1)"
REMOTE_RC=$?

if [ $REMOTE_RC -ne 0 ]; then
  echo "${BOLD}原因：连不上这个远程仓库${RESET}"
  echo "  ${DIM}$(echo "$REMOTE_OUT" | head -2)${RESET}"
  echo
  echo "${BOLD}逐个排查：${RESET}"
  echo "  ${YELLOW}·${RESET} 代理没开？ 启动 Clash Verge，然后重跑本脚本"
  echo "  ${YELLOW}·${RESET} 代理开了但 git 没走？ 手动配一下："
  echo "      ${DIM}git config --global http.https://github.com.proxy http://127.0.0.1:7897${RESET}"
  echo "  ${YELLOW}·${RESET} 仓库地址写错？ 去 GitHub 页面复制正确的地址"
  echo "  ${YELLOW}·${RESET} 仓库还没建？ 先去 https://github.com/new 建一个"
  echo
  exit 1
fi

REMOTE_BRANCH=""
if echo "$REMOTE_OUT" | grep -q 'refs/heads/main'; then
  REMOTE_BRANCH="main"
elif echo "$REMOTE_OUT" | grep -q 'refs/heads/master'; then
  REMOTE_BRANCH="master"
fi

if [ -z "$REMOTE_BRANCH" ]; then
  echo "${BOLD}原因：远程仓库是空的，但推送还是被拒了${RESET}"
  echo "  ${DIM}$(echo "$REMOTE_OUT" | head -3)${RESET}"
  echo
  echo "  多半是账号或权限问题："
  echo "  ${YELLOW}·${RESET} 这个仓库不属于你填的那个 GitHub 账号"
  echo "  ${YELLOW}·${RESET} 登录用的 Token 没有 repo 权限（去设置里重新生成一个）"
  echo
  exit 1
fi

# 远程有内容（建仓库时勾了 README / .gitignore / LICENSE）
echo "${BOLD}原因：GitHub 上那个仓库不是空的${RESET}"
echo "  ${DIM}远程分支：$REMOTE_BRANCH${RESET}"
echo

# 先看看远程到底有什么，避免盲目合并
REMOTE_FILES=""
if git fetch origin "$REMOTE_BRANCH" --depth=1 >/dev/null 2>&1; then
  REMOTE_FILES="$(git ls-tree --name-only "origin/$REMOTE_BRANCH" 2>/dev/null | head -20)"
fi

HAS_WEB=0
if [ -n "$REMOTE_FILES" ]; then
  echo "  ${BOLD}远程仓库里现在有这些东西：${RESET}"
  echo "$REMOTE_FILES" | sed 's/^/    /'
  echo
  if echo "$REMOTE_FILES" | grep -q -E '^(index\.html|manifest\.webmanifest|sw\.js|download/)'; then
    HAS_WEB=1
  fi
fi

if [ "$HAS_WEB" = "1" ]; then
  echo "  ${YELLOW}⚠  这个仓库里已经有网页文件了${RESET}"
  echo
  echo "  ${DIM}如果那就是你现在的调音器网页（Netlify 正从它发布），${RESET}"
  echo "  ${DIM}直接合并会把两套文件混在一起，可能弄乱线上站点。${RESET}"
  echo
  echo "  ${BOLD}建议这样做：${RESET}"
  echo "    1. 先回答 n，中止本次推送"
  echo "    2. 把你现有的仓库整个备份一份（或者先告诉我你仓库里有什么）"
  echo "    3. 用一个全新仓库来放这个 App 工程，最干净"
  echo
  echo "  ${DIM}如果那只是个 README、跟网页无关，那合并是安全的，答 y 就行。${RESET}"
  echo
else
  echo "  ${DIM}（看起来只是 README 之类的初始化文件，合并是安全的）${RESET}"
  echo
  echo "  合并一下就行，我来处理："
fi

printf "  把远程内容合并进来再推送？(y/n) > "
read -r MERGE_ANSWER
if [ "$MERGE_ANSWER" = "y" ]; then
  echo
  if git pull --rebase origin "$REMOTE_BRANCH"; then
    ok "已合并远程内容"
    echo
    if git push -u origin main; then
      echo
      echo "${GREEN}${BOLD}✅ 推送成功${RESET}"
      echo
      echo "  仓库地址：$REPO"
      echo
      echo "${BOLD}接下来：${RESET}"
      echo "  1. 仓库 Settings → Secrets and variables → Actions 加 4 个密钥"
      echo "     内容见 tools/keystore/密钥信息.txt："
      echo "       KEYSTORE_BASE64 / KEYSTORE_PASSWORD / KEY_PASSWORD / KEY_ALIAS"
      echo "  2. 仓库 Actions → 构建安卓 APK → Run workflow"
      echo "  3. Netlify 连上这个仓库，发布目录填 web"
      echo
      echo "  之后手机上打开 https://nan-tuner.cc 就能下载安装了。"
      echo
      exit 0
    fi
  fi
  err "合并后推送仍然失败，请把上面的报错发给我"
  exit 1
fi

echo
 echo "  ${DIM}你选了不合并。也可以自己处理：${RESET}"
 echo "  ${DIM}git pull --rebase origin $REMOTE_BRANCH && git push -u origin main${RESET}"
 exit 1
