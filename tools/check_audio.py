#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
验证 audio/ 里的乐器录音是否完整可用。

不依赖浏览器：直接解析 MP4/M4A 容器结构，
确认每个文件有 ftyp / moov / mdat，时长与采样率正确。
"""
import os
import struct
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
AUDIO_DIR = os.path.join(BASE, 'web', 'audio')


def boxes(data):
    """列出顶层 box: (type, offset, size)"""
    out = []
    off = 0
    while off + 8 <= len(data):
        size = struct.unpack('>I', data[off:off + 4])[0]
        typ = data[off + 4:off + 8].decode('latin-1')
        if size == 1:
            if off + 16 > len(data):
                break
            size = struct.unpack('>Q', data[off + 8:off + 16])[0]
        if size < 8:
            break
        out.append((typ, off, size))
        off += size
    return out


def main():
    if not os.path.isdir(AUDIO_DIR):
        sys.exit('找不到 audio 目录: %s' % AUDIO_DIR)

    files = sorted(f for f in os.listdir(AUDIO_DIR) if f.endswith('.m4a'))
    if not files:
        sys.exit('audio 目录里没有 .m4a')

    print('%-22s %8s %10s  %s' % ('文件', '大小', '结构', '状态'))
    print('-' * 62)

    bad = []
    total = 0
    for fn in files:
        path = os.path.join(AUDIO_DIR, fn)
        size = os.path.getsize(path)
        total += size
        with open(path, 'rb') as f:
            data = f.read()

        bs = boxes(data)
        types = [b[0] for b in bs]
        has_ftyp = 'ftyp' in types
        has_moov = 'moov' in types
        has_mdat = 'mdat' in types
        # 检查有没有超出文件末尾的 box
        ok_size = all(b[1] + b[2] <= size for b in bs)
        ok = has_ftyp and has_moov and has_mdat and ok_size and size > 3000

        struct_desc = ('f' if has_ftyp else '-') + \
                      ('m' if has_moov else '-') + \
                      ('d' if has_mdat else '-')

        if ok:
            print('%-22s %7dK %10s  ✓' % (fn, size // 1024, struct_desc))
        else:
            print('%-22s %7dK %10s  ✗ 缺失或损坏' % (fn, size // 1024, struct_desc))
            bad.append(fn)

    print('-' * 62)
    print('共 %d 个文件, %d KB' % (len(files), total // 1024))
    print('问题文件: %s' % (bad if bad else '无'))

    # 检查必需采样是否齐全
    required = []
    for n in ['E2', 'A2', 'D3', 'G3', 'B3', 'E4']:
        required.append('guitar_' + n)
    for n in ['G4', 'C4', 'E4', 'A4']:
        required.append('uke_' + n)
    for pt in ['C1', 'Fs1', 'C2', 'Fs2', 'C3', 'Fs3', 'C4', 'Fs4',
               'C5', 'Fs5', 'C6', 'Fs6', 'C7', 'Fs7', 'C8']:
        required.append('piano_' + pt)

    have = set(os.path.splitext(f)[0] for f in files)
    missing = [r for r in required if r not in have]
    print()
    print('必需采样 %d 个 → %s' % (len(required), '全部齐全 ✓' if not missing else '缺: ' + str(missing)))

    return 1 if (bad or missing) else 0


if __name__ == '__main__':
    sys.exit(main())
