#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
仿真验证 v2：加入真实琴弦的物理特性。

真实弦不是完美的周期信号，三个关键因素会削弱自相关：
  1. 非谐性（inharmonicity）：f_n = n·f0·√(1 + B·n²)
     弦有刚度，高次谐波被拉高。B 对吉他低音弦约 1e-4 ~ 1e-3。
  2. 拍频（beating）：同度弦 / 多模耦合导致幅度缓慢起伏
  3. 衰减 + 拨弦瞬态

2048 样本（46ms）对 E2（周期 12.1ms）只有 3.8 个周期，
非谐性会在这个长度内把自相关峰拉宽、拉低。
"""
import math
import random


def make_string(f0, sr, n, B=0.0004, noise=0.03, seed=0, decay=2.5, beat=1.2):
    """合成一根真实感的弦"""
    rnd = random.Random(seed)
    x = [0.0] * n

    # 谐波幅度：低音弦基频弱、2-3 次强
    amps = [0.32, 0.92, 0.52, 0.30, 0.17, 0.10]

    # 拍频：两个略微失谐的分量
    for k, amp in enumerate(amps, start=1):
        # 非谐性：高次谐波被拉高
        fk = k * f0 * math.sqrt(1 + B * k * k)
        ph = rnd.random() * 2 * math.pi
        # 拍频：同度双弦，频率差 0.1%
        fk2 = fk * (1 + 0.0006 * beat)
        for i in range(n):
            t = i / sr
            env = math.exp(-decay * t)
            w1 = 2 * math.pi * fk / sr * i + ph
            w2 = 2 * math.pi * fk2 / sr * i + ph
            x[i] += amp * env * (math.sin(w1) + math.sin(w2)) * 0.5

    # 拨弦瞬态：前 8ms 的宽带噪声
    trans = int(0.008 * sr)
    for i in range(min(trans, n)):
        x[i] += (rnd.random() * 2 - 1) * 0.35 * (1 - i / trans)

    for i in range(n):
        x[i] += (rnd.random() * 2 - 1) * noise

    peak = max(abs(v) for v in x) or 1.0
    return [v / peak for v in x]


def detect(buf, sr, min_f, max_f, size):
    n = len(buf)
    off = n - size
    size = min(size, n)
    mean = sum(buf[off:off + size]) / size

    min_lag = max(2, int(sr / max_f))
    max_lag = min(int(size * 2 / 3), int(sr / min_f))
    if max_lag <= min_lag:
        return None

    corr = {}
    best_val, best_pos = -1.0, -1

    for lag in range(min_lag, max_lag + 1):
        num = d1 = d2 = 0.0
        limit = size - lag
        for i in range(limit):
            a = buf[off + i] - mean
            b = buf[off + i + lag] - mean
            num += a * b
            d1 += a * a
            d2 += b * b
        den = math.sqrt(d1 * d2)
        nc = num / den if den > 1e-9 else 0.0
        corr[lag] = nc
        if nc > best_val:
            best_val, best_pos = nc, lag

    if best_pos < 0 or best_val < 0.55:
        return None

    thr = best_val * 0.93
    for lag in range(min_lag + 1, best_pos):
        if (corr.get(lag, 0) > thr
                and corr.get(lag, 0) >= corr.get(lag - 1, 0)
                and corr.get(lag, 0) >= corr.get(lag + 1, 0)):
            best_pos = lag
            break

    delta = 0.0
    if min_lag < best_pos < max_lag:
        y1 = corr.get(best_pos - 1, 0)
        y2 = corr.get(best_pos, 0)
        y3 = corr.get(best_pos + 1, 0)
        den = 2 * (y1 + y3 - 2 * y2)
        if den != 0:
            delta = -(y3 - y1) / den
            delta = max(-1.0, min(1.0, delta))

    period = best_pos + delta
    if period <= 0:
        return None
    f = sr / period
    if f < min_f or f > max_f:
        return None
    return f


def cents(f, target):
    return 1200 * math.log2(f / target)


def fold_octave(f, target):
    guard = 0
    while f > target * 1.6 and guard < 4:
        f /= 2
        guard += 1
    guard = 0
    while f < target / 1.6 and guard < 4:
        f *= 2
        guard += 1
    return f


SR = 44100
AVAIL = 8192
SEEDS = 10

CASES = [
    ('E2 6弦', 82.41),
    ('A2 5弦', 110.00),
    ('D3 4弦', 146.83),
    ('G3 3弦', 196.00),
    ('B3 2弦', 246.94),
    ('E4 1弦', 329.63),
]

print('=' * 84)
print('仿真 v2 · 含非谐性 + 拍频 + 衰减 + 拨弦瞬态')
print(f'每种情况跑 {SEEDS} 次不同噪声种子')
print('=' * 84)
print(f"{'弦':<10}{'2048 误差':>13}{'2048 准%':>10}"
      f"{'4096 误差':>13}{'4096 准%':>10}{'+折叠 误差':>13}{'+折叠 准%':>10}")
print('-' * 84)


def run_window(freq, size, fold=False):
    errs = []
    for seed in range(SEEDS):
        sig = make_string(freq, SR, AVAIL, seed=seed)
        f = detect(sig, SR, 70, 400, size)
        if f is None:
            continue
        if fold:
            f = fold_octave(f, freq)
        errs.append(cents(f, freq))
    return errs


for name, freq in CASES:
    e_old = run_window(freq, 2048)
    e_new = run_window(freq, 4096)
    e_fold = run_window(freq, 4096, fold=True)

    def stats(errs):
        if not errs:
            return '   全部失败', 0
        avg = sum(errs) / len(errs)
        ok = sum(1 for c in errs if abs(c) < 5) / len(errs) * 100
        return f'{avg:+10.1f}c', ok

    s_old, p_old = stats(e_old)
    s_new, p_new = stats(e_new)
    s_fold, p_fold = stats(e_fold)

    print(f'{name:<10}{s_old:>13}{p_old:>9.0f}%'
          f'{s_new:>13}{p_new:>9.0f}%'
          f'{s_fold:>13}{p_fold:>9.0f}%')

print()
print('说明：「误差」是同一种子下偏离真值的音分平均值，越小越好；')
print('      「准%」是落在 ±5 音分内的比例。')
