/* 始信音乐 · 乐器录音清单（自动生成，请勿手改）
 *
 * 由 tools/build_audio_manifest.py 生成。
 * 换过采样文件后重跑一次，哈希会变，SW 缓存随之失效。
 *
 * 生成时间：2026-10-17 16:47:39
 * 文件数：25
 */

window.AUDIO_MANIFEST = {
  "guitar_A2": "169ad729",
  "guitar_B3": "3a7516b7",
  "guitar_D3": "099dd298",
  "guitar_E2": "d913e13f",
  "guitar_E4": "d2a10722",
  "guitar_G3": "3257db1a",
  "piano_C1": "9457a80f",
  "piano_C2": "2af4e7bb",
  "piano_C3": "f8d7c43f",
  "piano_C4": "2d2e7c98",
  "piano_C5": "d93a7166",
  "piano_C6": "00a49a00",
  "piano_C7": "ba6255f6",
  "piano_C8": "13eb53d4",
  "piano_Fs1": "4afc17ad",
  "piano_Fs2": "c873acbf",
  "piano_Fs3": "ef6740fa",
  "piano_Fs4": "ac0cf521",
  "piano_Fs5": "d9188e85",
  "piano_Fs6": "3f65695e",
  "piano_Fs7": "fb08fd9b",
  "uke_A4": "4387972f",
  "uke_C4": "7d95c719",
  "uke_E4": "5c710deb",
  "uke_G4": "4b90e5f7"
};

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
