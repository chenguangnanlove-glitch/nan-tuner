/* ══════════════════════════════════════════════════════════════
   节拍器核心逻辑（纯计算，不碰 DOM / 音频）

   单独放在这里是为了能脱离浏览器测试 ——
   节拍器的重拍安排和速度术语都容易写错，需要能验证。
   ══════════════════════════════════════════════════════════════ */

/* ── 速度术语 ──
   按意大利传统区间划分，upTo 是上界（含）。
   中英对照方便教学时对应。 */
const TEMPO_TERMS = [
  { upTo: 40,       it: 'Grave',       cn: '庄板'   },
  { upTo: 60,       it: 'Largo',       cn: '广板'   },
  { upTo: 66,       it: 'Larghetto',   cn: '小广板' },
  { upTo: 76,       it: 'Adagio',      cn: '柔板'   },
  { upTo: 108,      it: 'Andante',     cn: '行板'   },
  { upTo: 120,      it: 'Moderato',    cn: '中板'   },
  { upTo: 168,      it: 'Allegro',     cn: '快板'   },
  { upTo: 200,      it: 'Presto',      cn: '急板'   },
  { upTo: Infinity, it: 'Prestissimo', cn: '最急板' },
];

function tempoTerm(bpm) {
  for (const t of TEMPO_TERMS) {
    if (bpm <= t.upTo) return t;
  }
  return TEMPO_TERMS[TEMPO_TERMS.length - 1];
}

/* ── 重拍安排 ──
   返回数组，每项取值：
     2 = 重拍（每小节第一拍）
     1 = 次重拍（分组头）
     0 = 弱拍

   规则（按先后顺序判断）：
     1. 分子 ≤ 4          → 只有第一拍重
     2. 分子是 3 的倍数     → 每三拍一组
        （6/8、9/8、12/8、6/4、9/4 ……）
     3. 3/8 特殊处理       → 当作单拍子，不分三组
     4. 分子是 4 的倍数     → 每四拍一组（12/16、16/16 这类）
     5. 其它（5、7 等）     → 第一拍重，其余弱
*/
function accentPattern(num, den) {
  const pattern = new Array(num).fill(0);
  if (num <= 0) return pattern;

  pattern[0] = 2;                       // 第一拍总是重拍

  if (num <= 4) return pattern;         // 单拍子，够简单

  // 复拍子：分子是 3 的倍数（且大于 3）
  const isCompound = (num % 3 === 0);
  // 3/8 视为单拍子（三拍等分，不按 3 分组）
  const shouldGroup = isCompound && !(den === 8 && num === 3);

  if (shouldGroup) {
    for (let i = 3; i < num; i += 3) {
      pattern[i] = 1;
    }
    return pattern;
  }

  // 四拍分组：12/16、16/16 这类复拍子
  if (num % 4 === 0) {
    for (let i = 4; i < num; i += 4) {
      pattern[i] = 1;
    }
    return pattern;
  }

  // 其它（5、7、11 ……）：第一拍重，其余弱
  return pattern;
}

/* ── 拍号范围 ──
   分子 2-12，分母 2/4/6/8/12 */
const NUM_MIN = 2;
const NUM_MAX = 12;
const DEN_VALUES = [2, 4, 6, 8, 12];

function clampNum(n) {
  return Math.max(NUM_MIN, Math.min(NUM_MAX, Math.round(n)));
}

function stepDen(den, dir) {
  let i = DEN_VALUES.indexOf(den);
  if (i < 0) i = 1;                     // 认不出来就当 4/4
  i = (i + dir + DEN_VALUES.length) % DEN_VALUES.length;
  return DEN_VALUES[i];
}

/* ── 常用拍号（下拉里的快捷项）── */
const METER_PRESETS = [
  { num: 2, den: 4 },
  { num: 3, den: 4 },
  { num: 4, den: 4 },
  { num: 6, den: 8 },
  { num: 2, den: 2 },
];

/* ── BPM 范围 ── */
const BPM_MIN = 30;
const BPM_MAX = 250;

function clampBpm(b) {
  return Math.max(BPM_MIN, Math.min(BPM_MAX, Math.round(b)));
}

/* ── 拖动灵敏度 ──
   转一圈（360°）大约变化多少 BPM。
   90 的手感：转 60° 变 15 BPM，转一圈变 90。
   太小调不动，太大调不准。 */
const DRAG_BPM_PER_TURN = 90;

/* ── 导出（供测试使用）── */
if (typeof module !== 'undefined' && module.exports) {
  module.exports = {
    TEMPO_TERMS, tempoTerm,
    accentPattern,
    NUM_MIN, NUM_MAX, DEN_VALUES, clampNum, stepDen,
    METER_PRESETS,
    BPM_MIN, BPM_MAX, clampBpm,
    DRAG_BPM_PER_TURN,
  };
}
