#!/bin/bash
# ==============================================================================
#  部署到你的 GitHub 仓库
#
#  做三件事：
#    1. 把你原来仓库里的 index.html 存档（不删，改名保留）
#    2. 把 App 工程全部推上去
#    3. 提示你在 Netlify 做一步设置
#
#  整个过程可回滚 —— 原来的文件在 Git 历史里，随时能还原。
#
#  用法：
#    bash tools/deploy.sh                          # 用默认仓库
#    bash tools/deploy.sh 用户名/仓库名
#    bash tools/deploy.sh --dry-run                # 只演示，不实际推送
# ==============================================================================

set -uo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
ROOT="$(cd "$HERE/.." && pwd)"

GREEN=$'\033[32m'; RED=$'\033[31m'; YELLOW=$'\033[33m'
BLUE=$'\033[34m'; DIM=$'\033[2m'; BOLD=$'\033[1m'; RESET=$'\033[0m'

ok()   { echo "  ${GREEN}✓${RESET} $*"; }
warn() { echo "  ${YELLOW}!${RESET} $*"; }
err()  { echo "  ${RED}✗${RESET} $*"; }
info() { echo "  ${BLUE}·${RESET} $*"; }
step() { echo; echo "${BOLD}$*${RESET}"; }
die()  { err "$1"; exit 1; }

DRY_RUN=0
REPO=""

for arg in "$@"; do
  case "$arg" in
    --dry-run) DRY_RUN=1 ;;
    *) REPO="$arg" ;;
  esac
done

# 默认仓库
if [ -z "$REPO" ]; then
  REPO="chenguangnanlove-glitch/nan-tuner"
fi

# 判断仓库类型
#   裸仓库（模拟 GitHub）      → git clone
#   git 工作区                → git clone
#   普通目录（纯文件）          → 直接复制
IS_LOCAL=0
if [ -d "$REPO" ]; then
  IS_LOCAL=1
  if [ -f "$REPO/HEAD" ] && [ -d "$REPO/objects" ]; then
    REPO_URL="$REPO"          # 裸仓库，可以当远程用
    REPO_DIR=""
  elif [ -d "$REPO/.git" ]; then
    REPO_URL="$REPO"          # git 工作区
    REPO_DIR=""
  else
    REPO_URL=""
    REPO_DIR="$REPO"          # 纯文件目录
  fi
elif [[ "$REPO" == https://* ]] || [[ "$REPO" == git@* ]]; then
  REPO_URL="$REPO"
  REPO_DIR=""
else
  REPO_URL="https://github.com/${REPO#/}"
  REPO_URL="${REPO_URL%.git}.git"
  REPO_DIR=""
fi

echo
echo "${BOLD}始信音乐 · 调音器 —— 部署${RESET}"
if [ "$DRY_RUN" = "1" ]; then
  echo "${YELLOW}${BOLD}[演示模式] 不会真的推送${RESET}"
fi
echo

# ════════════════════════════════════════════════════════════
step "0. 检查工程完整性"

[ -f "$ROOT/web/index.html" ]     || die "缺少 web/index.html，先跑 python3 tools/build_web.py"
[ -f "$ROOT/web/manifest.webmanifest" ] || die "缺少 web/manifest.webmanifest"
[ -f "$ROOT/android/app/build.gradle" ] || die "缺少安卓工程"
[ -f "$ROOT/netlify.toml" ]       || die "缺少 netlify.toml"
ok "网站文件齐全"
ok "安卓工程齐全"
ok "Netlify 配置齐全"

if [ ! -d "$ROOT/tools/keystore" ]; then
  warn "还没生成签名密钥（不影响部署网站，但 APK 构建会失败）"
  info "运行：bash tools/make_keystore.sh"
fi

# ════════════════════════════════════════════════════════════
step "1. 检查网络"

detect_proxy() {
  local ph pp
  ph=$(scutil --proxy 2>/dev/null | awk '/HTTPProxy/ {print $3; exit}')
  pp=$(scutil --proxy 2>/dev/null | awk '/HTTPPort/  {print $3; exit}')
  [ -n "$ph" ] && [ -n "$pp" ] && [ "$ph" != "0.0.0.0" ] && echo "$ph:$pp"
}

GIT_PROXY=()
if [ "$IS_LOCAL" = "0" ]; then
  # 注意：演示模式也需要配代理，因为克隆同样要联网
  PROXY="$(detect_proxy)"
  if curl --noproxy '*' -s -o /dev/null --max-time 6 "$REPO_URL" 2>/dev/null; then
    ok "直连可用"
  elif [ -n "$PROXY" ] && curl -x "http://$PROXY" -s -o /dev/null --max-time 8 "$REPO_URL" 2>/dev/null; then
    ok "通过代理可用（${PROXY}）"
    GIT_PROXY=(-c "http.proxy=http://$PROXY")
  else
    warn "网络看起来不通，先继续（下面可能失败）"
    if [ -n "$PROXY" ]; then
      info "检测到系统代理 ${PROXY}，已让 git 用上（仅本次）"
      GIT_PROXY=(-c "http.proxy=http://$PROXY")
    fi
  fi
else
  ok "本地路径，跳过网络检查"
fi

# ════════════════════════════════════════════════════════════
step "2. 获取你仓库的当前内容"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP" 2>/dev/null || true' EXIT
WORK="$TMP/repo"

if [ -n "$REPO_DIR" ]; then
  info "从本地目录复制"
  cp -R "$REPO_DIR" "$WORK"
else
  echo "  ${DIM}正在克隆…${RESET}"
  # 注意：macOS 自带 bash 3.2，空数组用 "${ARR[@]}" 展开会报 unbound variable。
  # 用 ${ARR[@]+"${ARR[@]}"} 这种写法才能兼容。
  if ! git ${GIT_PROXY[@]+"${GIT_PROXY[@]}"} clone --quiet "$REPO_URL" "$WORK" 2>"$TMP/clone.err"; then
    echo
    err "克隆失败"
    head -3 "$TMP/clone.err" | sed 's/^/    /'
    echo
    echo "  ${DIM}如果是私有仓库，需要先登录。试试手动克隆一次：${RESET}"
    echo "  ${DIM}git clone $REPO_URL${RESET}"
    exit 1
  fi
  ok "克隆成功"
fi
cd "$WORK"

OLD_BRANCH="$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)"
OLD_FILES="$(git ls-files 2>/dev/null | wc -l | tr -d ' ')"
info "当前分支：$OLD_BRANCH"
info "现有文件：$OLD_FILES 个"

if [ "$OLD_FILES" -gt 0 ]; then
  echo "  ${DIM}原有内容：${RESET}"
  git ls-files | head -10 | sed 's/^/      /'
fi

# ════════════════════════════════════════════════════════════
step "3. 变更预览"

CHANGES=()

# 原有 index.html 会被移到 archive/ 保留
if [ -f "index.html" ]; then
  CHANGES+=("把根目录的 index.html 移到 archive/old-index.html（保留备份）")
fi

CHANGES+=("新增 web/index.html —— 新版调音器（含 PWA 与下载入口）")
CHANGES+=("新增 web/manifest.webmanifest、web/sw.js、web/app-version.json")
CHANGES+=("新增 web/icons/ —— 4 个图标")
CHANGES+=("新增 web/download/index.html —— 手机下载页")
CHANGES+=("新增 android/ —— 安卓 App 工程")
CHANGES+=("新增 .github/workflows/build-apk.yml —— 自动打包流水线")
CHANGES+=("新增 netlify.toml —— 告诉 Netlify 从 web/ 发布")
CHANGES+=("新增 tools/ —— 各种辅助脚本")
CHANGES+=("新增 操作说明.md")

for c in "${CHANGES[@]}"; do
  echo "    ${GREEN}+${RESET} $c"
done

echo
echo "  ${BOLD}不会删除你原来的东西${RESET} —— index.html 只是挪个位置存起来。"

# ════════════════════════════════════════════════════════════
step "4. 执行变更"

# 存档旧的 index.html
if [ -f "index.html" ]; then
  mkdir -p archive
  git mv index.html archive/old-index.html 2>/dev/null || mv index.html archive/old-index.html
  ok "原 index.html 已存到 archive/old-index.html"
fi

# 复制新文件
# 把源目录的内容完整复制到目标位置。
#
# 坑：cp -R src dst 在 dst 已存在时，会复制成 dst/src/ 造成目录嵌套。
# （比如 android/android/app/...）所以先清掉目标再复制。
copy_in() {
  local src="$1" dst="$2"

  # 安全护栏：目标名不能为空，否则 rm -rf 会删掉当前目录
  [ -n "$dst" ] || return 1
  [ -e "$src" ] || return 0

  rm -rf "./$dst"
  mkdir -p "$(dirname "$dst")"
  cp -R "$src" "$dst"
}

copy_in "$ROOT/web"        "web"
copy_in "$ROOT/android"    "android"
copy_in "$ROOT/tools"      "tools"
copy_in "$ROOT/.github"    ".github"
copy_in "$ROOT/netlify.toml" "netlify.toml"
copy_in "$ROOT/.gitignore" ".gitignore"
copy_in "$ROOT/操作说明.md" "操作说明.md"

ok "新文件已铺好"

# 从仓库里清掉不该上传的
rm -f web/download/shixin-tuner.apk 2>/dev/null || true   # APK 由流水线生成
rm -rf tools/keystore 2>/dev/null || true                  # 签名密钥（绝对不能上传）
rm -f tools/.build-state.json tools/repo-report.txt 2>/dev/null || true
find . -name ".DS_Store" -delete 2>/dev/null || true
find . -name "__pycache__" -type d -prune -exec rm -rf {} + 2>/dev/null || true
find . -name "*.pyc" -delete 2>/dev/null || true

# ════════════════════════════════════════════════════════════
step "5. 统计"

NEW_COUNT="$(git add -A --dry-run 2>/dev/null | wc -l | tr -d ' ')"
info "本次变更 $NEW_COUNT 项"

git add -A
STAGED="$(git diff --staged --name-only | wc -l | tr -d ' ')"
info "已暂存 $STAGED 个文件"

# 安全检查：必须在 git add 之后，否则暂存区是空的，检查等于白做
if git diff --staged --name-only 2>/dev/null | grep -qE '\.p12$|\.jks$|\.keystore$'; then
  echo
  err "危险：签名密钥在待提交列表里"
  git diff --staged --name-only | grep -E '\.p12$|\.jks$|\.keystore$' | sed 's/^/    /'
  echo
  echo "  ${DIM}请检查 tools/keystore/ 是否被 .gitignore 排除了${RESET}"
  exit 1
fi

if git diff --staged --name-only 2>/dev/null | grep -qE '__pycache__|\.pyc$'; then
  warn "暂存区里有 Python 缓存文件，正在移除"
  git diff --staged --name-only | grep -E '__pycache__|\.pyc$' | while read -r f; do
    git rm --cached --quiet "$f" 2>/dev/null || true
  done
fi

ok "已确认没有密钥或缓存文件混入"

# ════════════════════════════════════════════════════════════
if [ "$DRY_RUN" = "1" ]; then
  step "演示结束"
  echo
  echo "  以上就是要做的全部事情。"
  echo "  确认没问题后，去掉 --dry-run 再跑一次就会真的推送。"
  echo
  exit 0
fi

step "6. 提交并推送"

git config user.email >/dev/null 2>&1 || {
  warn "git 身份没配置"
  printf "  你的名字 > "
  read -r N
  printf "  你的邮箱 > "
  read -r E
  [ -n "$N" ] && git config user.name "$N"
  [ -n "$E" ] && git config user.email "$E"
}

# 先看看有没有实际变化。
# 如果没变化，说明之前已经成功部署过了（比如上次推完又跑了一次），
# 这时候不该报「提交失败」吓人，而是友好地告知无需重复。
ALREADY_DEPLOYED=0
if git diff --staged --quiet 2>/dev/null; then
  ALREADY_DEPLOYED=1
  ok "仓库内容已经是最新（之前已经部署过）"
else
  git commit --quiet -m "接入安卓 App 与 PWA 支持

把网页版调音器升级为可安装的安卓 App：
- PWA 支持：可添加到主屏幕、离线可用
- 下载页：手机扫码即可下载安装 APK
- 安卓工程：WebView 外壳，含麦克风授权与离线兜底
- 自动构建：GitHub Actions 打包 APK 并发布

原有的 index.html 已移动到 archive/old-index.html 备份。
Netlify 发布目录改为 web/（由 netlify.toml 指定）。" \
    || die "提交失败"

  ok "已提交"
fi

# ────────────────────────────────────────────
#  推送（带自动重试）
#
#  代理网络经常会抖动一下，单次失败不代表真失败。
#  这里最多试 3 次，网络类错误才重试；认证类错误直接报。
# ────────────────────────────────────────────

# 网络类错误（可重试）
IS_NETWORK_ERROR() {
  grep -qE "SSL_ERROR_SYSCALL|SSL_ERROR_SSL|Could not resolve host|Operation timed out|Failed to connect|Connection reset|Connection timed out|early EOF|RPC failed|Recv failure|Send failure|the remote end hung up" "$1" 2>/dev/null
}

# 认证/权限类错（不重试，重试也没用）
IS_AUTH_ERROR() {
  grep -qE "Authentication failed|could not read Username|Permission to .* denied|refusing to allow|Repository not found|terminal prompts disabled" "$1" 2>/dev/null
}

# 降低大文件推送出问题的概率
git config http.postBuffer 524288000 2>/dev/null || true
git config http.lowSpeedLimit 1000 2>/dev/null || true
git config http.lowSpeedTime 60 2>/dev/null || true

MAX_TRIES=3
TRY=1
PUSH_OK=0

if [ "$ALREADY_DEPLOYED" = "1" ]; then
  ok "无需重复推送"
  PUSH_OK=1
fi

while [ "${PUSH_OK}" -eq 0 ] && [ "$TRY" -le "$MAX_TRIES" ]; do
  if [ "$TRY" -eq 1 ]; then
    echo "  ${DIM}正在推送…${RESET}"
  else
    echo "  ${YELLOW}第 ${TRY} 次尝试…${RESET}"
  fi

  : > "$TMP/push.err"

  if git ${GIT_PROXY[@]+"${GIT_PROXY[@]}"} push origin "$OLD_BRANCH" 2>"$TMP/push.err"; then
    PUSH_OK=1
    break
  fi

  # 认证问题不重试
  if IS_AUTH_ERROR "$TMP/push.err"; then
    break
  fi

  # 网络问题：等一下再试
  if IS_NETWORK_ERROR "$TMP/push.err" && [ "$TRY" -lt "$MAX_TRIES" ]; then
    WAIT=$((TRY * 3))
    echo "  ${DIM}网络抖了一下，等 ${WAIT} 秒自动重试…${RESET}"
    sleep "$WAIT"
  fi

  TRY=$((TRY + 1))
done

if [ "$PUSH_OK" -eq 0 ]; then
  echo
  err "推送失败"
  echo
  grep -iE "error|fatal|denied|failed|rejected|refusing" "$TMP/push.err" 2>/dev/null \
    | head -5 | sed 's/^/    /'
  echo

  if IS_AUTH_ERROR "$TMP/push.err"; then
    if grep -q "refusing to allow" "$TMP/push.err"; then
      echo "  ${BOLD}原因：通行证缺「workflow」权限${RESET}"
      echo
      echo "  ${BOLD}.github/workflows/${RESET} 里的文件需要额外权限才能上传。"
      echo "  补上就好："
      echo "    ${DIM}1. 打开 https://github.com/settings/tokens${RESET}"
      echo "    ${DIM}2. 点开描述写着 Shixin Tuner Deploy 的那条${RESET}"
      echo "    ${DIM}3. 勾上 workflow（在 repo 那一大项的下面）${RESET}"
      echo "    ${DIM}4. 拉到最下面点 Update token${RESET}"
      echo
      echo "  改完不用重新输通行证，直接重新跑本脚本即可。"
    else
      echo "  ${BOLD}原因：登录凭据有问题${RESET}"
      echo
      echo "  在终端里手动推一次，按提示操作："
      echo "    ${DIM}cd $WORK && git push origin $OLD_BRANCH${RESET}"
      echo
      echo "  提示输密码时粘贴 Personal Access Token（不是账号密码）。"
      echo "  没有 token？去这里生成，勾选 repo 和 workflow："
      echo "    ${DIM}https://github.com/settings/tokens${RESET}"
    fi
  else
    echo "  ${BOLD}原因：网络不通${RESET}"
    echo
    echo "  试了 ${MAX_TRIES} 次都没连上 GitHub。"
    echo
    echo "  排查方向："
    echo "    ${YELLOW}·${RESET} 换个代理节点试试（现在的节点可能不稳）"
    echo "    ${YELLOW}·${RESET} 在 Clash 里测一下延迟，挑个快的节点"
    echo "    ${YELLOW}·${RESET} 确认 GitHub 没在 Clash 的分流规则里走了直连"
    echo
    echo "  网络恢复后重新跑本脚本即可（会重新走一遍，很快）。"
  fi

  echo
  echo "  ${DIM}（临时目录会被清理，重新跑本脚本即可）${RESET}"
  exit 1
fi

if [ "$TRY" -gt 1 ]; then
  ok "推送成功（第 ${TRY} 次尝试）"
else
  ok "推送成功"
fi

# ════════════════════════════════════════════════════════════
step "7. 完成"

echo
echo "  ${GREEN}${BOLD}✅ 代码已经在 GitHub 上了${RESET}"
echo
echo "  仓库：https://github.com/${REPO:-$REPO_DIR}"
echo
echo "  ${BOLD}接下来做两件事：${RESET}"
echo
echo "  ${BOLD}① 确认 Netlify 的发布目录${RESET}"
echo "     打开 Netlify → 你的站点 → Site configuration → Build & deploy"
echo "     把 ${BOLD}Publish directory${RESET} 改成：${GREEN}web${RESET}"
echo "     （netlify.toml 里已经写了，但 UI 里确认一下更保险）"
echo
echo "  ${BOLD}② 配置 APK 构建密钥${RESET}"
echo "     1. 打开仓库 → Settings → Secrets and variables → Actions"
echo "     2. 添加这 4 个 Secret（内容在 tools/keystore/密钥信息.txt）："
echo "          KEYSTORE_BASE64"
echo "          KEYSTORE_PASSWORD"
echo "          KEY_PASSWORD"
echo "          KEY_ALIAS"
echo "     3. 打开仓库 → Actions → 「构建安卓 APK」→ Run workflow"
echo
echo "  等几分钟，APK 就打包好了，手机打开 https://nan-tuner.cc/download/ 即可下载。"
echo
