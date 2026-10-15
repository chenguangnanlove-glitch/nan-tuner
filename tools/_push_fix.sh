#!/bin/bash
# 推送编译错误的修复

cd "$(dirname "$0")/.." || exit 1

MSG_FILE="$(mktemp)"
cat > "$MSG_FILE" <<'MSG'
修复编译错误：onReceivedError 改用 WebResourceErrorCompat

构建报错：
  MainActivity.java:191: onReceivedError(WebView, WebResourceRequest, WebResourceError)
  cannot override ... in WebViewClientCompat — overridden method is final

WebViewClientCompat 把框架的 WebResourceError 版本声明为 final，
必须改用 androidx 的 WebResourceErrorCompat 版本。

已用真实的 androidx.webkit 1.12.1 与 Android 框架类库验证：
- WebViewClientCompat.onReceivedError(…, WebResourceErrorCompat) 可覆盖
- shouldOverrideUrlLoading / shouldInterceptRequest 均为合法覆盖
- 38 个方法调用全部存在（含继承链查找）

同时新增三个 API 校验工具，改代码后可先本地验证再推送。
MSG

export SHIXIN_COMMIT_MSG="$(cat "$MSG_FILE")"
rm -f "$MSG_FILE"

bash tools/deploy.sh
