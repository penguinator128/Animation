// Soundtrack, written in code: rendered offline with the Web Audio API, returned as a 16-bit WAV.
// Soft textures build with the assembly (gate clicks that spin up, a plucked note per pride stripe,
// an opening pad and air bed), a breath of silence, then one clean hit as the logo lands.
window.renderSoundtrack = async function () {
  const SR = 48000, DUR = 10, B = 60 / 90, LAND = 11 * B;
  const ac = new OfflineAudioContext(2, SR * DUR, SR);
  const master = ac.createGain(); master.gain.value = 0.9;
  const comp = ac.createDynamicsCompressor();
  comp.threshold.value = -14; comp.ratio.value = 3; comp.attack.value = 0.004; comp.release.value = 0.2;
  master.connect(comp).connect(ac.destination);
  const hz = m => 440 * Math.pow(2, (m - 69) / 12);
  let seed = 7; const rnd = () => (seed = (seed * 16807) % 2147483647) / 2147483647 * 2 - 1;
  const noise = (secs) => { const b = ac.createBuffer(1, SR * secs, SR), d = b.getChannelData(0); for (let i = 0; i < d.length; i++) d[i] = rnd(); return b; };
  const pan = (v) => { const p = ac.createStereoPanner(); p.pan.value = v; p.connect(master); return p; };
  const GAP = LAND - 0.09; // a breath of silence right before the hit

  // air bed: filtered noise whose filter opens as the pieces assemble
  { const s = ac.createBufferSource(); s.buffer = noise(DUR); const f = ac.createBiquadFilter(); f.type = 'lowpass'; f.Q.value = 0.4;
    f.frequency.setValueAtTime(220, 0); f.frequency.exponentialRampToValueAtTime(700, 3 * B); f.frequency.exponentialRampToValueAtTime(5200, GAP);
    const g = ac.createGain(); g.gain.setValueAtTime(0.0001, 0); g.gain.exponentialRampToValueAtTime(0.035, 1.2); g.gain.exponentialRampToValueAtTime(0.085, GAP - 0.02); g.gain.linearRampToValueAtTime(0, GAP);
    s.connect(f).connect(g).connect(master); s.start(0); }

  // pad: D major colour, detuned pairs, lowpass opening from bar 1
  { const f = ac.createBiquadFilter(); f.type = 'lowpass'; f.Q.value = 0.7;
    f.frequency.setValueAtTime(300, 0); f.frequency.exponentialRampToValueAtTime(600, 3 * B); f.frequency.exponentialRampToValueAtTime(3200, GAP);
    const g = ac.createGain(); g.gain.setValueAtTime(0.0001, 0); g.gain.exponentialRampToValueAtTime(0.02, 3 * B); g.gain.exponentialRampToValueAtTime(0.11, GAP - 0.02); g.gain.linearRampToValueAtTime(0, GAP);
    f.connect(g).connect(master);
    for (const m of [50, 57, 62, 66, 69]) for (const det of [-6, 6]) {
      const o = ac.createOscillator(); o.type = 'triangle'; o.frequency.value = hz(m); o.detune.value = det;
      const og = ac.createGain(); og.gain.value = 0.12; o.connect(og).connect(f); o.start(0); o.stop(GAP + 0.01); } }

  // gate clicks: one per film step, spinning up bar by bar
  const steps = [0, 2, 3, 4, 5, 6, 7, 7.5, 8, 8.5, 9, 9.5, 10, 10.5];
  const nb = noise(0.2);
  steps.forEach((b, i) => {
    const t = b * B, lvl = 0.1 + 0.12 * i / steps.length;
    const s = ac.createBufferSource(); s.buffer = nb; const f = ac.createBiquadFilter(); f.type = 'bandpass'; f.frequency.value = 1800 + 90 * i; f.Q.value = 1.6;
    const g = ac.createGain(); g.gain.setValueAtTime(lvl, t); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.05);
    s.connect(f).connect(g).connect(pan(-0.25)); s.start(t); s.stop(t + 0.08);
    const o = ac.createOscillator(); o.frequency.setValueAtTime(110, t); o.frequency.exponentialRampToValueAtTime(60, t + 0.06);
    const og = ac.createGain(); og.gain.setValueAtTime(lvl * 1.4, t); og.gain.exponentialRampToValueAtTime(0.0001, t + 0.09);
    o.connect(og).connect(pan(-0.25)); o.start(t); o.stop(t + 0.1);
  });

  // one pluck per pride stripe as it enters (D pentatonic, rising), a softer octave as it leans
  const pluck = (t, m, lvl, p, decay) => {
    for (const [mult, a] of [[1, 1], [2, 0.35], [3, 0.12]]) {
      const o = ac.createOscillator(); o.type = 'sine'; o.frequency.value = hz(m) * mult;
      const g = ac.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(lvl * a, t + 0.008); g.gain.exponentialRampToValueAtTime(0.0001, t + decay / mult);
      o.connect(g).connect(pan(p)); o.start(t); o.stop(t + decay + 0.05);
    }
  };
  const notes = [62, 64, 66, 69, 71, 74];
  [4, 5, 5.5, 6, 6.5, 7].forEach((b, i) => pluck(b * B, notes[i], 0.16, 0.35, 0.9));
  [8, 8.3, 8.6, 8.9, 9.2, 9.5].forEach((b, i) => pluck(b * B, notes[i] + 12, 0.07, 0.45, 0.5));

  // the hit: low thump, short transient, bright D add9 chord that rings through the hold bar
  { const t = LAND;
    const o = ac.createOscillator(); o.frequency.setValueAtTime(140, t); o.frequency.exponentialRampToValueAtTime(42, t + 0.14);
    const g = ac.createGain(); g.gain.setValueAtTime(0.0001, t); g.gain.exponentialRampToValueAtTime(0.95, t + 0.004); g.gain.exponentialRampToValueAtTime(0.0001, t + 0.9);
    o.connect(g).connect(master); o.start(t); o.stop(t + 1);
    const s = ac.createBufferSource(); s.buffer = noise(0.1); const f = ac.createBiquadFilter(); f.type = 'lowpass'; f.frequency.value = 4500;
    const sg = ac.createGain(); sg.gain.setValueAtTime(0.35, t); sg.gain.exponentialRampToValueAtTime(0.0001, t + 0.05);
    s.connect(f).connect(sg).connect(master); s.start(t);
    const end = DUR - 0.02;
    [[38, .2], [50, .16], [57, .12], [62, .1], [66, .08], [69, .07], [76, .05], [81, .03]].forEach(([m, lvl], i) => {
      for (const det of [-4, 4]) {
        const c = ac.createOscillator(); c.type = i < 2 ? 'sine' : 'triangle'; c.frequency.value = hz(m); c.detune.value = det;
        const cg = ac.createGain(); cg.gain.setValueAtTime(0.0001, t); cg.gain.exponentialRampToValueAtTime(lvl, t + 0.006);
        cg.gain.exponentialRampToValueAtTime(lvl * 0.25, t + 1.3); cg.gain.exponentialRampToValueAtTime(lvl * 0.06, end - 0.3); cg.gain.linearRampToValueAtTime(0, end);
        c.connect(cg).connect(pan(det < 0 ? -0.3 : 0.3)); c.start(t); c.stop(end + 0.01);
      } }); }

  const buf = await ac.startRendering();
  const L = buf.getChannelData(0), R = buf.getChannelData(1);
  let peak = 0; for (let i = 0; i < L.length; i++) peak = Math.max(peak, Math.abs(L[i]), Math.abs(R[i]));
  const gain = 0.89 / peak; // normalise to about -1 dBFS
  const n = L.length, dv = new DataView(new ArrayBuffer(44 + n * 4));
  const str = (o, s) => { for (let i = 0; i < s.length; i++) dv.setUint8(o + i, s.charCodeAt(i)); };
  str(0, 'RIFF'); dv.setUint32(4, 36 + n * 4, true); str(8, 'WAVE'); str(12, 'fmt '); dv.setUint32(16, 16, true);
  dv.setUint16(20, 1, true); dv.setUint16(22, 2, true); dv.setUint32(24, SR, true); dv.setUint32(28, SR * 4, true);
  dv.setUint16(32, 4, true); dv.setUint16(34, 16, true); str(36, 'data'); dv.setUint32(40, n * 4, true);
  for (let i = 0; i < n; i++) {
    dv.setInt16(44 + i * 4, Math.max(-1, Math.min(1, L[i] * gain)) * 32767, true);
    dv.setInt16(46 + i * 4, Math.max(-1, Math.min(1, R[i] * gain)) * 32767, true);
  }
  const bytes = new Uint8Array(dv.buffer); let bin = '';
  for (let i = 0; i < bytes.length; i += 0x8000) bin += String.fromCharCode.apply(null, bytes.subarray(i, i + 0x8000));
  return btoa(bin);
};
