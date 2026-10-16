/* ══════════════════════════════════════════════════════════════
   节拍器音频引擎

   为什么不用 setTimeout 直接发声：
     setTimeout 的误差会累积（每拍偏几毫秒，一分钟后能差出半拍），
     而且页面切到后台会被浏览器降频到 1 次/秒，节拍直接乱掉。

   做法：Web Audio 的预调度（look-ahead scheduler）
     · 每 25ms 醒一次（这个频率够低，不影响性能）
     · 每次把未来 100ms 内该响的拍子，提前"预约"给音频时钟
     · 到点由音频硬件精确触发，不依赖 JS 定时精度
     结果：切后台、页面卡顿，节拍都不会漂。
   ══════════════════════════════════════════════════════════════ */

const LOOKAHEAD_MS = 25;      // 多久检查一次
const SCHEDULE_AHEAD = 0.1;   // 提前多少秒预排（秒）

function Metronome() {
  this.ctx = null;

  this.bpm = 120;
  this.num = 4;               // 分子
  this.den = 4;               // 分母
  this.pattern = [2, 0, 0, 0];  // 重拍安排

  this.playing = false;
  this.currentBeat = -1;      // 当前拍（用于界面高亮）
  this.nextNoteTime = 0;      // 下一拍的音频时间
  this.beatIndex = 0;         // 排到第几拍了
  this.timerId = null;

  this.onBeat = null;         // 每拍的回调（用于界面闪动）

  // 音量（0-1）
  this.volume = 0.7;
}

/* ── 拍间隔（秒）──
   一拍的长度 = 全音符 ÷ 分母。
   而全音符 = 4 个四分音符，所以：

     拍长 = (60 / BPM) × (4 / 分母)

   验证：
     分母 4  → 60/BPM × 1    = 四分音符
     分母 8  → 60/BPM × 0.5  = 八分音符
     分母 2  → 60/BPM × 2    = 二分音符
     分母 6  → 60/BPM × 2/3  = 六分音符
     分母 12 → 60/BPM × 1/3  = 十二分音符
*/
Metronome.prototype.beatDuration = function () {
  const quarter = 60 / this.bpm;
  return quarter * (4 / this.den);
};

/* ── 确保音频上下文 ── */
Metronome.prototype.ensureCtx = function () {
  if (!this.ctx) {
    const AC = window.AudioContext || window.webkitAudioContext;
    this.ctx = new AC();
  }
  if (this.ctx.state === 'suspended') {
    this.ctx.resume();
  }
  return this.ctx;
};

/* ── 合成一声"嗒" ──
   用正弦波 + 极快衰减，接近木鱼/电子节拍器的听感。
   重拍：音高更高、更长、更响。
   次重拍：中间水平。
   弱拍：最低最轻。

   at  —— 何时发声（音频时间轴）
   kind —— 2 重拍 / 1 次重拍 / 0 弱拍
*/
Metronome.prototype.click = function (at, kind) {
  const ctx = this.ctx;

  // 音高：重拍高，弱拍低
  const freq = kind === 2 ? 1760 : (kind === 1 ? 1320 : 1050);
  // 音量：重拍响
  const gain = kind === 2 ? 1.0 : (kind === 1 ? 0.72 : 0.52);
  // 衰减：重拍稍长，让重音更"实"
  const decay = kind === 2 ? 0.055 : 0.038;

  const osc = ctx.createOscillator();
  const env = ctx.createGain();

  osc.type = 'sine';
  osc.frequency.setValueAtTime(freq, at);
  // 轻微下滑，声音更自然（不滑会像纯电子音，偏"硬"）
  osc.frequency.exponentialRampToValueAtTime(freq * 0.86, at + decay);

  // 音量包络：瞬间起、快速落
  const peak = gain * this.volume * 0.42;
  env.gain.setValueAtTime(0, at);
  env.gain.linearRampToValueAtTime(peak, at + 0.0012);
  env.gain.exponentialRampToValueAtTime(0.0001, at + decay);

  osc.connect(env);
  env.connect(ctx.destination);

  osc.start(at);
  osc.stop(at + decay + 0.01);

  // 起音那一瞬加一点噪声，模拟"敲击"的质感。
  // 纯正弦听起来太"电子"，加噪声后更像木头/鼓。
  const nLen = Math.floor(ctx.sampleRate * 0.006);
  if (nLen > 0) {
    const buf = ctx.createBuffer(1, nLen, ctx.sampleRate);
    const data = buf.getChannelData(0);
    for (let i = 0; i < nLen; i++) {
      // 越往后越弱
      data[i] = (Math.random() * 2 - 1) * (1 - i / nLen) * 0.5;
    }
    const noise = ctx.createBufferSource();
    const nEnv = ctx.createGain();
    const nFilter = ctx.createBiquadFilter();

    noise.buffer = buf;
    // 带通滤波，让噪声集中在敲击频段，不刺耳
    nFilter.type = 'bandpass';
    nFilter.frequency.value = freq * 0.55;
    nFilter.Q.value = 1.2;

    nEnv.gain.setValueAtTime(peak * 0.5, at);
    nEnv.gain.exponentialRampToValueAtTime(0.0001, at + 0.012);

    noise.connect(nFilter);
    nFilter.connect(nEnv);
    nEnv.connect(ctx.destination);

    noise.start(at);
    noise.stop(at + 0.02);
  }
};

/* ── 调度循环 ──
   把 SCHEDULE_AHEAD 秒内该响的拍子全部预约出去。 */
Metronome.prototype.scheduler = function () {
  const ctx = this.ctx;
  if (!ctx || !this.playing) return;

  while (this.nextNoteTime < ctx.currentTime + SCHEDULE_AHEAD) {
    const kind = this.pattern[this.beatIndex] !== undefined
      ? this.pattern[this.beatIndex]
      : 0;

    this.click(this.nextNoteTime, kind);

    // 通知界面（延后到真正发声的时刻再闪，避免提前闪）
    if (this.onBeat) {
      const delay = (this.nextNoteTime - ctx.currentTime) * 1000;
      const idx = this.beatIndex;
      setTimeout(() => {
        if (this.playing) this.onBeat(idx, kind);
      }, Math.max(0, delay));
    }

    // 推进到下一拍
    this.nextNoteTime += this.beatDuration();
    this.beatIndex = (this.beatIndex + 1) % this.num;
  }
};

/* ── 开始 ── */
Metronome.prototype.start = function () {
  if (this.playing) return;
  this.ensureCtx();

  this.playing = true;
  this.beatIndex = 0;
  // 稍微延后一点起拍，避免第一声被切掉
  this.nextNoteTime = this.ctx.currentTime + 0.06;

  this.scheduler();
  this.timerId = setInterval(() => this.scheduler(), LOOKAHEAD_MS);
};

/* ── 停止 ── */
Metronome.prototype.stop = function () {
  this.playing = false;
  if (this.timerId) {
    clearInterval(this.timerId);
    this.timerId = null;
  }
  this.beatIndex = 0;
  this.currentBeat = -1;
};

/* ── 改速度（运行中也能立即生效）── */
Metronome.prototype.setBpm = function (bpm) {
  this.bpm = clampBpm(bpm);
};

/* ── 改拍号 ──
   同时重算重拍安排。如果正在响，下一小节生效（不打断当前小节）。 */
Metronome.prototype.setMeter = function (num, den) {
  this.num = clampNum(num);
  this.den = den;
  this.pattern = accentPattern(this.num, this.den);

  if (this.beatIndex >= this.num) {
    this.beatIndex = 0;
  }
};

/* ── 拍号文字 ── */
Metronome.prototype.meterLabel = function () {
  return this.num + '/' + this.den;
};
