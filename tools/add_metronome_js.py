#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
把节拍器的 JS 插入 web/index.html。

分三部分插进去：
  1. metronome_core.js  —— 重拍计算、速度术语、范围常量
  2. metronome_engine.js —— Web Audio 预调度
  3. 界面控制             —— 胶囊切换、拍号面板、圆环拖动、播放按钮

不改动调音器原有的任何一行 JS。
"""

import os
import re
import shutil
import sys

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
WEB = os.path.join(BASE, "web", "index.html")
CORE = os.path.join(BASE, "tools", "metronome_core.js")
ENGINE = os.path.join(BASE, "tools", "metronome_engine.js")

GREEN = "\033[32m"; RED = "\033[31m"; YELLOW = "\033[33m"
DIM = "\033[2m"; BOLD = "\033[1m"; RESET = "\033[0m"

MARKER = "<!-- METRONOME-JS-INSERTED -->"
MARKER_END = "<!-- /METRONOME-JS-INSERTED -->"

text = open(WEB, encoding="utf-8").read()

if 'id="pageMetro"' not in text:
    print(f"{RED}✗ 先运行 add_metronome.py 插入 HTML 结构{RESET}")
    sys.exit(1)

core_js = open(CORE, encoding="utf-8").read()
engine_js = open(ENGINE, encoding="utf-8").read()

# 去掉 core 里给 node 用的导出段（浏览器不需要，留着会报 module is not defined）
core_js = re.sub(
    r"/\* ── 导出（供测试使用）── \*/.*?^\}$",
    "",
    core_js,
    flags=re.S | re.M,
).strip()

# ══════════════════════════════════════════════════════════
#  界面控制
# ══════════════════════════════════════════════════════════

UI_JS = r"""
/* ══════════════════════════════════════════════════════════════
   节拍器界面（由 tools/add_metronome_js.py 插入）
   ══════════════════════════════════════════════════════════════ */

(function initMetronome(){

  /* ══════════════════════════════════════════════════════
     元素
     ══════════════════════════════════════════════════════ */

  const el = {
    tabs:       document.getElementById('appTabs'),
    tabTuner:   document.getElementById('tabTuner'),
    tabMetro:   document.getElementById('tabMetro'),
    pageTuner:  document.getElementById('pageTuner'),
    pageMetro:  document.getElementById('pageMetro'),

    meterBtn:   document.getElementById('meterBtn'),
    meterLabel: document.getElementById('meterLabel'),
    meterSheet: document.getElementById('meterSheet'),
    meterClose: document.getElementById('meterClose'),
    numWheel:   document.getElementById('numWheel'),
    denWheel:   document.getElementById('denWheel'),

    ring:       document.getElementById('metroRing'),
    center:     document.getElementById('ringCenter'),
    progress:   document.getElementById('ringProgress'),
    pulseRing:  document.getElementById('pulseRing'),
    bpmValue:   document.getElementById('bpmValue'),
    bpmInput:   document.getElementById('bpmInput'),
    bpmTerm:    document.getElementById('bpmTerm'),
    beatDots:   document.getElementById('beatDots'),
    vol:        document.getElementById('volSeg'),
  };

  // 缺任何一个都不往下走 —— 后面到处在用，
  // 中途爆 null 更难查。
  const missing = Object.keys(el).filter(k => !el[k]);
  if (missing.length) {
    console.warn('[节拍器] 缺少元素，已跳过初始化：', missing.join(', '));
    return;
  }

  const metro = new Metronome();

  /* ── 圆环尺寸 → CSS 变量 ──
     量出可用空间写进 --ring-size，圆内的数字、术语按它缩放。
     必须量「外层区域」而不是圆环自己：
     圆环的宽高由 --ring-size 决定，若观察它自己，
     就会形成「尺寸→字号→尺寸」的反馈环，越缩越小。 */
  function syncRingSize(){
    const area = el.ring.parentElement;
    if (!area) return;

    const maxD = parseFloat(getComputedStyle(area).getPropertyValue('--ring-max')) || 310;
    const w = area.clientWidth;
    const h = area.clientHeight;

    if (!(w > 0) || !(h > 0)) return;

    // 取「可用宽 / 可用高 / 上限」三者最小 —— 三者都与字号无关。
    const d = Math.max(120, Math.min(w, h, maxD));
    el.ring.style.setProperty('--ring-size', d.toFixed(1) + 'px');
  }
  if (window.ResizeObserver) {
    new ResizeObserver(syncRingSize).observe(el.ring.parentElement);
  }
  syncRingSize();
  window.addEventListener('resize', syncRingSize);
  window.addEventListener('orientationchange', syncRingSize);

  /* ── 音量：16 格分段刻度 ──
     指针位置 → 音量（连续映射，不卡格）。
     同时也支持键盘方向键，以及 role=slider 的取值播报。 */
  const VOL_SEGS = 16;

  function buildVolSegs(){
    let h = '';
    for (let i = 0; i < VOL_SEGS; i++) h += '<i></i>';
    el.vol.innerHTML = h;
  }

  function paintVolume(){
    const n = Math.round(metro.volume * VOL_SEGS);
    const items = el.vol.children;
    for (let i = 0; i < items.length; i++) {
      items[i].classList.toggle('on', i < n);
    }
    el.vol.setAttribute('aria-valuenow', String(Math.round(metro.volume * 100)));
  }

  function setVolFromX(clientX){
    const r = el.vol.getBoundingClientRect();
    if (r.width <= 0) return;
    const t = (clientX - r.left) / r.width;
    metro.volume = Math.max(0, Math.min(1, t));
    paintVolume();
  }

  let volDown = false;
  el.vol.addEventListener('pointerdown', (e) => {
    volDown = true;
    try { el.vol.setPointerCapture(e.pointerId); } catch (_) {}
    setVolFromX(e.clientX);
  });
  el.vol.addEventListener('pointermove', (e) => {
    if (volDown) setVolFromX(e.clientX);
  });
  function volUp(e){
    volDown = false;
    try { el.vol.releasePointerCapture(e.pointerId); } catch (_) {}
  }
  el.vol.addEventListener('pointerup', volUp);
  el.vol.addEventListener('pointercancel', volUp);

  el.vol.addEventListener('keydown', (e) => {
    let d = 0;
    if (e.key === 'ArrowLeft' || e.key === 'ArrowDown')  d = -0.05;
    else if (e.key === 'ArrowRight' || e.key === 'ArrowUp') d = 0.05;
    else if (e.key === 'Home') { metro.volume = 0; paintVolume(); e.preventDefault(); return; }
    else if (e.key === 'End')  { metro.volume = 1; paintVolume(); e.preventDefault(); return; }
    else return;
    e.preventDefault();
    metro.volume = Math.max(0, Math.min(1, metro.volume + d));
    paintVolume();
  });

  buildVolSegs();
  paintVolume();

  // 是否正在输入速度（切页、空格键都要看这个）
  let editing = false;
  let currentPage = 'tuner';

  /* ══════════════════════════════════════════════════════
     页面切换（胶囊滑块）
     ══════════════════════════════════════════════════════ */

  function switchPage(page) {
    if (page === currentPage) return;
    currentPage = page;

    const isMetro = (page === 'metro');

    el.tabTuner.classList.toggle('active', !isMetro);
    el.tabMetro.classList.toggle('active',  isMetro);
    el.tabs.dataset.index = isMetro ? '1' : '0';

    el.pageTuner.classList.toggle('active', !isMetro);
    el.pageMetro.classList.toggle('active',  isMetro);

    document.body.dataset.page = page;

    if (isMetro) {
      // 切到节拍页：停掉调音器，释放麦克风。
      // running/stop 在调音器自己的闭包里，这里拿不到，
      // 所以看 .app.listening（由调音器在开听时加上），再点它的按钮触发停止。
      try {
        const app = document.getElementById('app');
        const tunerBtn = document.getElementById('startBtn');
        if (app && app.classList.contains('listening') && tunerBtn) {
          tunerBtn.click();
        }
      } catch (e) {}

      // 节拍页初始是隐藏的（display:none），刚切过来时之前量的尺寸是 0。
      // ResizeObserver 通常会补触发，但不依赖它 —— 等布局落定后显式量一次。
      requestAnimationFrame(syncRingSize);
    } else {
      // 切回调音页：节拍器停掉。
      // 它的声音会被麦克风收进去，导致音高检测乱跳。
      if (metro.playing) stopMetro();
    }

    // 正在输入速度的话，先结束输入（避免输入框一直张着）
    if (editing) endEdit(true);

    // 顺手收起设置面板 —— 切页后还张着会显得乱
    try {
      const panel = document.getElementById('settingsPanel');
      const gear  = document.getElementById('settingsBtn');
      if (panel && panel.classList.contains('open')) {
        panel.classList.remove('open');
        if (gear) gear.classList.remove('active');
      }
    } catch (e) {}
  }

  el.tabTuner.addEventListener('click', () => switchPage('tuner'));
  el.tabMetro.addEventListener('click', () => switchPage('metro'));

  /* ══════════════════════════════════════════════════════
     拍号选择面板
     ══════════════════════════════════════════════════════ */

  /* ── 双列滚轮 ──
     不用原生滚动：每项按相对位置绝对定位，拖动换算成索引变化。
     这样能精确控制居中，也方便每跨一格震一下。 */
  const WHEEL_H  = 46;                             // 单项高度
  const NUM_LIST = [];
  for (let n = NUM_MIN; n <= NUM_MAX; n++) NUM_LIST.push(n);
  const DEN_LIST = DEN_VALUES.slice();

  function buzz(ms){
    try { if (navigator.vibrate) navigator.vibrate(ms || 8); } catch (_) {}
  }

  // 只渲染中间 ±2 行 —— 屏幕上看得见的就这几行，多了也白画
  function makeWheel(rootEl, list, getIdx, onPick){
    function render(){
      const cur = getIdx();
      let h = '';
      for (let k = -2; k <= 2; k++) {
        const i = cur + k;
        if (i < 0 || i >= list.length) continue;
        const cls = k === 0 ? 'sel' : (Math.abs(k) === 1 ? 'near' : 'far');
        h += '<div class="meter-wheel-item ' + cls + '" '
           + 'style="transform:translateY(' + (k * WHEEL_H) + 'px)">'
           + list[i] + '</div>';
      }
      rootEl.innerHTML = h;
      rootEl.setAttribute('aria-valuemin', String(list[0]));
      rootEl.setAttribute('aria-valuemax', String(list[list.length - 1]));
      rootEl.setAttribute('aria-valuenow', String(list[cur]));
    }

    let drag = null;
    rootEl.addEventListener('pointerdown', (e) => {
      drag = { y: e.clientY, start: getIdx() };
      try { rootEl.setPointerCapture(e.pointerId); } catch (_) {}
    });

    rootEl.addEventListener('pointermove', (e) => {
      if (!drag) return;
      // 往上拖 = 列表往上走 = 索引增大
      const step = Math.round((drag.y - e.clientY) / WHEEL_H);
      let i = drag.start + step;
      i = Math.max(0, Math.min(list.length - 1, i));
      if (i !== getIdx()) {
        onPick(i);
        buzz(8);
        render();
      }
    });

    function endDrag(){ drag = null; }
    rootEl.addEventListener('pointerup', endDrag);
    rootEl.addEventListener('pointercancel', endDrag);

    // 键盘：上下键一格一格走
    rootEl.addEventListener('keydown', (e) => {
      let d = 0;
      if (e.key === 'ArrowUp' || e.key === 'ArrowLeft') d = -1;
      else if (e.key === 'ArrowDown' || e.key === 'ArrowRight') d = 1;
      else return;
      e.preventDefault();
      const i = Math.max(0, Math.min(list.length - 1, getIdx() + d));
      if (i !== getIdx()) { onPick(i); buzz(8); render(); }
    });

    render();
    return render;
  }

  const renderNumWheel = makeWheel(
    el.numWheel, NUM_LIST,
    () => NUM_LIST.indexOf(metro.num),
    (i) => setMeter(NUM_LIST[i], metro.den)
  );
  const renderDenWheel = makeWheel(
    el.denWheel, DEN_LIST,
    () => DEN_LIST.indexOf(metro.den),
    (i) => setMeter(metro.num, DEN_LIST[i])
  );

  function renderWheels(){ renderNumWheel(); renderDenWheel(); }

  function openSheet() {
    el.meterSheet.classList.add('open');
  }
  function closeSheet() {
    el.meterSheet.classList.remove('open');
  }

  el.meterBtn.addEventListener('click', openSheet);
  el.meterClose.addEventListener('click', closeSheet);
  // 点遮罩也能关
  el.meterSheet.addEventListener('click', (e) => {
    if (e.target === el.meterSheet) closeSheet();
  });

  /* ══════════════════════════════════════════════════════
     拍号设置
     ══════════════════════════════════════════════════════ */

  function setMeter(num, den) {
    metro.setMeter(num, den);

    el.meterLabel.textContent = metro.num + '/' + metro.den;
    renderWheels();
    buildBeatDots();
    clearBeatHighlight();
  }

  /* ══════════════════════════════════════════════════════
     拍点指示
     ══════════════════════════════════════════════════════ */

  function buildBeatDots() {
    el.beatDots.innerHTML = '';
    // 拍子多的话缩小间距，避免挤成一片
    el.beatDots.classList.toggle('dense', metro.num > 8);

    for (let i = 0; i < metro.num; i++) {
      const d = document.createElement('div');
      d.className = 'beat-dot' + (metro.pattern[i] === 2 ? ' accent' : '');
      el.beatDots.appendChild(d);
    }
  }

  function clearBeatHighlight() {
    el.beatDots.querySelectorAll('.beat-dot').forEach(d => d.classList.remove('on'));
    el.pulseRing.classList.remove('beat');
  }

  function highlightBeat(index, kind) {
    const dots = el.beatDots.querySelectorAll('.beat-dot');
    dots.forEach((d, i) => d.classList.toggle('on', i === index));

    // 脉冲：先移除再加，让动画能重播
    el.pulseRing.classList.remove('beat');
    void el.pulseRing.offsetWidth;
    el.pulseRing.classList.add('beat');
  }

  /* ══════════════════════════════════════════════════════
     BPM 显示
     ══════════════════════════════════════════════════════ */

  // 进度弧：270° 的弧，按 BPM 在范围内的比例显示
  const RING_R = 90;
  const RING_C = 2 * Math.PI * RING_R;      // 周长
  const ARC_LEN = RING_C * 0.75;            // 270° 的弧长

  function updateProgress() {
    const ratio = (metro.bpm - BPM_MIN) / (BPM_MAX - BPM_MIN);
    const len = ARC_LEN * Math.max(0, Math.min(1, ratio));
    el.progress.style.strokeDasharray = len + ' ' + RING_C;
  }

  function paintBpm() {
    el.bpmValue.textContent = metro.bpm;
    const t = tempoTerm(metro.bpm);
    el.bpmTerm.textContent = t.it;
    updateProgress();
  }

  function setBpm(bpm) {
    const old = metro.bpm;
    metro.setBpm(bpm);
    if (metro.bpm === old) return;
    paintBpm();
  }

  /* ══════════════════════════════════════════════════════
     键盘输入 BPM（点数字进入）
     ══════════════════════════════════════════════════════ */

  function beginEdit() {
    if (editing) return;
    editing = true;

    el.bpmInput.value = metro.bpm;
    el.bpmValue.classList.add('hidden');
    el.bpmInput.classList.add('show');

    // 聚焦并全选，方便直接覆盖输入
    setTimeout(() => {
      el.bpmInput.focus();
      try { el.bpmInput.setSelectionRange(0, 9); } catch (e) {}
    }, 30);
  }

  function endEdit(commit) {
    if (!editing) return;
    editing = false;

    if (commit) {
      const raw = (el.bpmInput.value || '').replace(/[^0-9]/g, '');
      if (raw) {
        setBpm(clampBpm(parseInt(raw, 10)));
      }
    }

    el.bpmInput.classList.remove('show');
    el.bpmValue.classList.remove('hidden');
    paintBpm();
  }

  el.bpmValue.addEventListener('click', (e) => {
    e.stopPropagation();
    beginEdit();
  });

  el.bpmInput.addEventListener('input', () => {
    // 只留数字，最多 3 位
    const clean = el.bpmInput.value.replace(/[^0-9]/g, '').slice(0, 3);
    if (clean !== el.bpmInput.value) el.bpmInput.value = clean;
  });

  el.bpmInput.addEventListener('keydown', (e) => {
    e.stopPropagation();          // 不要触发空格键的播放/停止
    if (e.key === 'Enter') {
      e.preventDefault();
      endEdit(true);
      el.bpmInput.blur();
    } else if (e.key === 'Escape') {
      e.preventDefault();
      endEdit(false);
      el.bpmInput.blur();
    }
  });

  // 失焦就确认（手机上点空白处也会走这里）
  el.bpmInput.addEventListener('blur', () => endEdit(true));

  // 在输入框上的触摸/鼠标操作不要传给圆环
  ['pointerdown', 'pointermove', 'pointerup', 'click'].forEach(ev => {
    el.bpmInput.addEventListener(ev, (e) => e.stopPropagation());
  });

  /* ══════════════════════════════════════════════════════
     圆环拖动调速
     ══════════════════════════════════════════════════════ */

  let drag = null;

  // 触点相对圆心的角度（度，顺时针，0 = 正右）
  function angleAt(clientX, clientY) {
    const rect = el.ring.getBoundingClientRect();
    const cx = rect.left + rect.width / 2;
    const cy = rect.top + rect.height / 2;
    return Math.atan2(clientY - cy, clientX - cx) * 180 / Math.PI;
  }

  function onDown(e) {
    // 圆形内的输入要素不算拖动：数字、输入框
    if (e.target.closest) {
      if (e.target.closest('.ring-bpm')) return;
      if (e.target.closest('.ring-bpm-input')) return;
    }

    // 正在输入速度时，先结束输入，不要误触拖动
    if (editing) return;

    const x = e.clientX, y = e.clientY;
    drag = {
      last:   angleAt(x, y),
      start:  metro.bpm,
      accum:  0,
      moved:  false,
    };

    try { el.ring.setPointerCapture(e.pointerId); } catch (err) {}
  }

  function onMove(e) {
    if (!drag) return;

    const a = angleAt(e.clientX, e.clientY);

    // 角度增量，处理跨越 ±180° 的回绕
    let d = a - drag.last;
    if (d > 180) d -= 360;
    if (d < -180) d += 360;

    drag.accum += d;
    drag.last = a;

    // 位移太小就当没动 —— 避免手指抖动误改速度
    if (!drag.moved) {
      if (Math.abs(drag.accum) < 3) return;
      drag.moved = true;
    }

    const deltaBpm = drag.accum / 360 * DRAG_BPM_PER_TURN;
    setBpm(Math.round(drag.start + deltaBpm));

    e.preventDefault();
  }

  function onUp(e) {
    if (!drag) return;
    const wasDrag = drag.moved;
    drag = null;
    try { el.ring.releasePointerCapture(e.pointerId); } catch (err) {}

    // 只是点了一下（没拖动）→ 当作播放/停止
    if (!wasDrag) {
      if (metro.playing) stopMetro(); else startMetro();
    }
  }

  /* ══════════════════════════════════════════════════════
     播放 / 停止

     没有单独的播放按钮 —— 点圆环任意位置（含圆心）即开始/停止。
     播放中通过数字变主色来表示状态。
     ══════════════════════════════════════════════════════ */

  function startMetro() {
    metro.onBeat = (index, kind) => highlightBeat(index, kind);
    metro.start();

    el.bpmValue.classList.add('playing');
    el.center.classList.add('playing');
    el.ring.setAttribute('aria-label', '节拍器运行中，点一下停止');
    document.body.classList.add('metro-live');
    if (window.syncSettingsLive) window.syncSettingsLive();
  }

  function stopMetro() {
    metro.stop();

    el.bpmValue.classList.remove('playing');
    el.center.classList.remove('playing');
    el.ring.setAttribute('aria-label', '节拍器已停止，点一下开始');
    clearBeatHighlight();
    document.body.classList.remove('metro-live');
    if (window.syncSettingsLive) window.syncSettingsLive();
  }

  el.ring.addEventListener('pointerdown', onDown);
  el.ring.addEventListener('pointermove', onMove);
  el.ring.addEventListener('pointerup', onUp);
  el.ring.addEventListener('pointercancel', () => { drag = null; });

  // 空格键快捷开关（输入框里打字时不触发）
  document.addEventListener('keydown', (e) => {
    if (e.code !== 'Space') return;
    const tag = (e.target.tagName || '').toLowerCase();
    if (tag === 'input' || tag === 'textarea') return;
    if (editing) return;                              // 正在输入速度
    if (currentPage !== 'metro') return;
    if (el.meterSheet.classList.contains('open')) return;
    e.preventDefault();
    if (metro.playing) stopMetro(); else startMetro();
  });

  /* ══════════════════════════════════════════════════════
     切到后台时清掉高亮（播放不停 —— 用户可能就想让它响着）
     ══════════════════════════════════════════════════════ */

  document.addEventListener('visibilitychange', () => {
    if (document.hidden) clearBeatHighlight();
  });

  /* ══════════════════════════════════════════════════════
     初始化
     ══════════════════════════════════════════════════════ */

  setMeter(4, 4);
  metro.setBpm(120);
  paintBpm();                 // 初始化时直接画，不能走 setBpm（值没变会跳过）
  el.ring.setAttribute('aria-label', '节拍器已停止，点一下开始');
  document.body.dataset.page = 'tuner';
  el.tabs.dataset.index = '0';

})();
"""

# ══════════════════════════════════════════════════════════
#  组装
# ══════════════════════════════════════════════════════════

BLOCK = f"""{MARKER}
<script>
/* ════════════════════════════════════════════════════════════
   节拍器（由 tools/add_metronome_js.py 插入）

     1. 核心逻辑 —— 重拍计算、速度术语、范围常量
     2. 音频引擎 —— Web Audio 预调度，保证节拍稳定
     3. 界面控制 —— 胶囊切换、拍号面板、圆环拖动、播放按钮
   ════════════════════════════════════════════════════════════ */

/* ─────────── 1. 核心逻辑 ─────────── */
{core_js}

/* ─────────── 2. 音频引擎 ─────────── */
{engine_js}

/* ─────────── 3. 界面控制 ─────────── */
{UI_JS}
</script>
{MARKER_END}
"""

# ── 幂等：用正则匹配整个块并替换（标记外的空白完全不动）──
#
# 不能“删了再插”—— 两边的空行结构不对称，会累积。
pattern = re.compile(
    re.escape(MARKER) + r".*?" + re.escape(MARKER_END),
    re.S)

if pattern.search(text):
    text = pattern.sub(lambda m: BLOCK.rstrip("\n"), text, count=1)
    action = "已更新"
else:
    idx = text.rfind("</script>")
    if idx < 0:
        print(f"{RED}✗ 找不到 </script>{RESET}")
        sys.exit(1)

    idx += len("</script>")
    text = text[:idx] + "\n\n" + BLOCK + text[idx:]
    action = "已插入"

shutil.copy2(WEB, WEB + ".pre-metro-js.bak")
with open(WEB, "w", encoding="utf-8") as f:
    f.write(text)

print(f"{GREEN}✓ 节拍器 JS {action}{RESET}")
print()
print(f"  核心逻辑  {len(core_js):>7,} 字符")
print(f"  音频引擎  {len(engine_js):>7,} 字符")
print(f"  界面控制  {len(UI_JS):>7,} 字符")
print(f"  合计      {len(BLOCK):>7,} 字符")
print()
