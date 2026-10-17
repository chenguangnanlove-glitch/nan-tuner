#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
给乐器录音生成内容哈希清单，写进 web/audio-manifest.js。

为什么需要：
  web/sw.js 对静态资源是「缓存优先」，音频的 URL 又没有任何版本参数。
  一旦换了采样，老用户的 Service Worker 会永远从缓存里拿旧文件 ——
  听不到新的音色，而且永远修不好（除非用户手动清缓存）。

做法：
  每个文件的 URL 后面带上内容哈希（audio/guitar_E2.m4a?v=d03ec7dc）。
  页面里用 AudioManifest.url(key) 拼 URL，哈希变了 URL 就变了，
  缓存自然失效。

  哈希取自文件内容，所以不需要人记着改版本号 —— 跑这个脚本就行。

用法：
  python3 tools/build_audio_manifest.py

自动被 build_web.py 调用，一般不用手动跑。
"""
import hashlib
import os

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE, 'web', 'audio')
OUT = os.path.join(BASE, 'web', 'audio-manifest.js')

HEADER = '''/* 始信音乐 · 乐器录音清单（自动生成，请勿手改）
 *
 * 由 tools/build_audio_manifest.py 生成。
 * 换过采样文件后重跑一次，哈希会变，SW 缓存随之失效。
 *
 * 生成时间：%s
 * 文件数：%d
 */

window.AUDIO_MANIFEST = %s;

(function () {
  'use strict';
  var M = window.AUDIO_MANIFEST;
  /* 拼出带版本参数的 URL。没有清单项时退化为不带版本（首次加载兜底）。 */
  window.AudioManifest = {
    url: function (key, ext) {
      ext = ext || '.m4a';
      var v = M[key];
      return 'audio/' + key + ext + (v ? '?v=' + v : '');
    },
    has: function (key) { return Object.prototype.hasOwnProperty.call(M, key); }
  };
})();
'''


def main() -> int:
    if not os.path.isdir(AUDIO_DIR):
        print('找不到音频目录:', AUDIO_DIR)
        return 1

    files = sorted(
        f for f in os.listdir(AUDIO_DIR)
        if f.lower().endswith(('.m4a', '.mp3', '.ogg', '.wav'))
    )
    if not files:
        print('音频目录是空的:', AUDIO_DIR)
        return 1

    entries = []
    total = 0
    for fn in files:
        path = os.path.join(AUDIO_DIR, fn)
        h = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(65536), b''):
                h.update(chunk)
        digest = h.hexdigest()[:8]
        key = os.path.splitext(fn)[0]
        entries.append('  "%s": "%s"' % (key, digest))
        total += os.path.getsize(path)

    body = '{\n' + ',\n'.join(entries) + '\n}'

    import datetime
    stamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

    with open(OUT, 'w', encoding='utf-8') as f:
        f.write(HEADER % (stamp, len(files), body))

    print('✅ 音频清单已生成')
    print('   %d 个文件, %d KB' % (len(files), total // 1024))
    print('   → web/audio-manifest.js')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
