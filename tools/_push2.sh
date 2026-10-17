#!/bin/bash
# 推送 .gitignore 与工作流的修复

cd "$(dirname "$0")/.." || exit 1

MSG_FILE="$(mktemp)"
cat > "$MSG_FILE" <<'MSG'
修复：APK 无法提交回仓库（.gitignore 冲突）

上一轮构建日志显示：
  The following paths are ignored by one of your .gitignore files:
  web/download/*-tuner.apk
  ##[error]Process completed with exit code 1

原因：.gitignore 里的 *.apk 把构建产物也拦住了，
导致 GitHub Actions 打包成功后无法把 APK 提交回仓库，
Netlify 因此拿不到安装包。

改动：
- .gitignore 增加 !web/download/*.apk 例外，
  只有这个目录下的 APK 允许提交（那是给用户下载的正式包）
- 工作流触发路径加上 .gitignore，
  这样以后改忽略规则也能自动重新构建

顺带说明：上一轮 APK 已经编译成功（BUILD SUCCESSFUL in 31s，
产物约 1.1MB），只是卡在最后搬运环节。
MSG

export SHIXIN_COMMIT_MSG="$(cat "$MSG_FILE")"
rm -f "$MSG_FILE"

bash tools/deploy.sh
