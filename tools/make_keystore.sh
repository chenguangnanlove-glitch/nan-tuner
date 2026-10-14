#!/bin/bash
# ==============================================================================
#  生成 APK 签名密钥（安卓 App 的「身份证」）
#
#  为什么需要它：
#    安卓要求每个 App 必须签名才能安装。只要是同一个密钥签的名，新版本就能
#    覆盖安装旧版本、且数据不丢。密钥一旦丢失，就只能卸载重装（数据会清空）。
#
#  用法：
#    bash tools/make_keystore.sh            # 首次生成
#    bash tools/make_keystore.sh --force    # 重新生成（覆盖旧的，慎用！）
#
#  生成后得到：
#    tools/keystore/shixin-tuner.p12     密钥库文件（务必离线备份，不要外传）
#    tools/keystore/密钥信息.txt          密码与别名
#    tools/keystore/KEYSTORE_BASE64.txt   给 GitHub Secrets 用的编码内容
#
#  这个目录已被 .gitignore 排除，不会上传到 GitHub。
# ==============================================================================

set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
KS_DIR="$HERE/keystore"
KS_FILE="$KS_DIR/shixin-tuner.p12"
INFO_FILE="$KS_DIR/密钥信息.txt"
B64_FILE="$KS_DIR/KEYSTORE_BASE64.txt"

ALIAS="shixin"
VALIDITY_DAYS=10000        # 约 27 年

FORCE=0
if [ "${1:-}" = "--force" ]; then FORCE=1; fi

# ---------------------------------------------------------------- 防误覆盖
if [ -f "$KS_FILE" ] && [ "$FORCE" -ne 1 ]; then
  echo "⚠  签名密钥已存在：$KS_FILE"
  echo
  echo "   如果已经用它发布过 App，请不要重新生成 —— 换密钥就无法覆盖更新了。"
  echo "   确实要重新生成，运行：bash tools/make_keystore.sh --force"
  echo
  echo "   已有的密码信息在：$INFO_FILE"
  exit 1
fi

mkdir -p "$KS_DIR"
chmod 700 "$KS_DIR"

# ---------------------------------------------------------------- 生成随机强密码
# 只用字母和数字，避免特殊字符在命令行 / CI 配置里被转义
PASS="$(python3 -c "
import secrets, string
alphabet = string.ascii_letters + string.digits
print(''.join(secrets.choice(alphabet) for _ in range(28)))
")"

TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

echo "① 生成 RSA 2048 私钥与自签证书…"
openssl req -x509 -newkey rsa:2048 \
  -keyout "$TMP/key.pem" -out "$TMP/cert.pem" \
  -days "$VALIDITY_DAYS" -nodes \
  -subj "/CN=Shixin Music Tuner/O=Shixin Music/OU=Mobile/C=CN" 2>/dev/null

echo "② 打包成 Java / Android 可读的 PKCS12 密钥库…"
# 关键：显式指定 3DES 系列算法。macOS 自带 openssl 默认的 RC2-40，Java 读不了。
openssl pkcs12 -export \
  -out "$KS_FILE" \
  -inkey "$TMP/key.pem" -in "$TMP/cert.pem" \
  -name "$ALIAS" \
  -keypbe PBE-SHA1-3DES -certpbe PBE-SHA1-3DES -macalg SHA1 \
  -passout "pass:$PASS"

echo "③ 校验密钥库…"
if ! openssl pkcs12 -info -in "$KS_FILE" -passin "pass:$PASS" -noout >/dev/null 2>&1; then
  echo "❌ 校验失败，请重试"
  rm -f "$KS_FILE"
  exit 1
fi

ALGO="$(openssl pkcs12 -info -in "$KS_FILE" -passin "pass:$PASS" -noout 2>&1 \
        | grep -m1 'Shrouded Keybag' | sed 's/.*: //' || true)"

echo "④ 写出密码信息与 GitHub 用编码…"
cat > "$INFO_FILE" <<EOF
始信音乐 · 调音器 —— APK 签名密钥信息
生成时间：$(date '+%Y-%m-%d %H:%M:%S')

密钥库文件 ：shixin-tuner.p12
密钥库密码 ：$PASS
密钥别名   ：$ALIAS
密钥密码   ：$PASS

【重要】请立刻备份这个文件夹，最好存到网盘或 U 盘。
       密钥丢了以后，App 就只能卸载重装，用户数据会清空。

【GitHub Secrets 需要填这 4 个值】
  KEYSTORE_BASE64    = 见 KEYSTORE_BASE64.txt 的内容（脚本已复制到剪贴板）
  KEYSTORE_PASSWORD  = $PASS
  KEY_PASSWORD       = $PASS
  KEY_ALIAS          = $ALIAS
EOF

base64 -i "$KS_FILE" > "$B64_FILE"

# 顺手把 base64 复制到剪贴板，方便直接粘贴到 GitHub
if command -v pbcopy >/dev/null 2>&1; then
  pbcopy < "$B64_FILE"
  COPIED="（已复制到剪贴板，可直接粘贴）"
else
  COPIED=""
fi

chmod 600 "$KS_FILE" "$INFO_FILE" "$B64_FILE"

echo
echo "✅ 完成"
echo
echo "   密钥库    ：$KS_FILE"
echo "   算法      ：$ALGO   ← Java / Android 兼容"
echo "   密钥别名  ：$ALIAS"
echo "   密钥密码  ：$PASS"
echo
echo "   KEYSTORE_BASE64.txt $COPIED"
echo
echo "──────────────────────────────────────────────────────────"
echo "  下一步：打开 tools/keystore/密钥信息.txt，"
echo "         把 4 个值填进 GitHub 仓库的 Secrets 里"
echo "──────────────────────────────────────────────────────────"
echo
echo "⚠  请立刻备份整个 keystore 文件夹。"
