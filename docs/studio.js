/* 스튜디오 — 이론 표출 · 전체 사전 검색 · 안내형 음 입력 · 시각화.
 *
 * 여기 있는 것은 전부 이미 검증된 코덱(encoder/decoder) 위에 놓인
 * 표면이다. 규칙을 새로 만들지 않는다 — 보여 주고, 들려 주고,
 * 눌러 볼 수 있게 할 뿐이다. */
(function () {
  "use strict";
  const D = window.SORIMUN, K = D.codes, B = D.banks;
  const R = window.SoriRead, W = window.SoriWrite;
  const $ = s => document.querySelector(s);
  const el = (t, a, c) => { const n = document.createElement(t);
    if (a) for (const k in a) n.setAttribute(k, a[k]);
    if (c != null) n.textContent = c; return n; };
  const NS = "http://www.w3.org/2000/svg";
  const sv = (t, a) => { const n = document.createElementNS(NS, t);
    for (const k in a) n.setAttribute(k, a[k]); return n; };
  const NAMES = ["C","C#","D","D#","E","F","F#","G","G#","A","A#","B"];
  const nm = m => NAMES[((m % 12) + 12) % 12] + (Math.floor(m / 12) - 1);
  const COLOR = { major:"#e9b44c", minor:"#9b8ec4", neutral:"#5f8fa6",
                  marker:"#4a5a6d" };
  const Q_NAME = ["major", "minor", "neutral"];
  const Q_KO = { major:"장", minor:"단", neutral:"중성" };
  const tonicOfNote = n => (n.qi == null || n.idx == null)
    ? K.tonics[0]
    : K.tonics[(n.idx + 3 * Math.max(0, n.tier || 0) + 5 * n.qi)
               % K.tonics.length];

  /* ── 화음 하나 울리기 ── */
  let ctx = null;
  function audio() {
    if (!ctx) ctx = new (window.AudioContext || window.webkitAudioContext)();
    if (ctx.state === "suspended") ctx.resume();
    return ctx;
  }
  const fq = m => 440 * Math.pow(2, (m - 69) / 12);
  function playChord(pitches, dur = .7, vel = 90) {
    const c = audio(), t0 = c.currentTime + .02;
    for (const p of pitches) {
      const o = c.createOscillator(), g = c.createGain();
      o.type = "triangle"; o.frequency.value = fq(p);
      const amp = Math.pow(vel / 127, 1.6) * .25 / pitches.length;
      g.gain.setValueAtTime(0, t0);
      g.gain.linearRampToValueAtTime(amp, t0 + .015);
      g.gain.setValueAtTime(amp * .8, t0 + dur * .7);
      g.gain.exponentialRampToValueAtTime(.0001, t0 + dur);
      o.connect(g); g.connect(c.destination);
      o.start(t0); o.stop(t0 + dur + .05);
    }
  }
  const clampRoot = (v, root) => Math.min(root, K.highest - v[v.length - 1]);

  /* ── 이펙터 — 재생에만 얹는다. 내려받는 WAV 는 언제나 마른 소리다. ──
     Hologram Microcosm 의 짜임을 빌렸다:
       입력 → 그레인 엔진(마이크로루프·그래뉼·글리치) → 핑퐁 딜레이
            → 공명 필터(+변조) → 공간 → 출력.
     그레인 엔진은 AudioWorklet 이 4초 링버퍼에서 조각을 붙잡아
     되풀고, 흩뿌리고, 옥타브를 올린다. 전부 템포에 물린다. */
  window.__fx = { prog: "haze", grainDiv: .5, activity: .55, shape: .6,
                  pitchSet: "shimmer", grainMix: .45,
                  dlyDiv: 0, dlyFb: .38, dlyMix: .28,
                  cut: 5200, res: .8, modRate: .18, modDepth: .25,
                  revType: "bloom", revMix: .5, preDelay: .03, tone: 3600,
                  loop: false, tempo: 72 };
  const _imp = {};
  function impulse(c, type) {
    if (_imp[type]) return _imp[type];
    // 종류마다 길이·감쇠·질감이 다르다.
    // 질감 0 보통 · 1 밝게(고역) · 2 어둡게(저역) · 3 피어남(느린 부풂+저역)
    const spec = { room: [1.0, 3.6, 0], chamber: [0.55, 4.6, 0],
                   hall: [3.0, 2.1, 0], cathedral: [5.6, 1.7, 0],
                   plate: [1.7, 1.5, 1],
                   glacial: [8.5, 1.35, 2], bloom: [6.0, 1.8, 3],
                 }[type] || [2.4, 2.2, 0];
    const n = Math.floor(c.sampleRate * spec[0]);
    const b = c.createBuffer(2, n, c.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = b.getChannelData(ch);
      let prev = 0;
      for (let i = 0; i < n; i++) {
        let v = (Math.random() * 2 - 1) * Math.pow(1 - i / n, spec[1]);
        const mode = spec[2];
        if (mode === 1) { const hp = v - prev; prev = v; v = hp; }
        else if (mode === 2) { v = prev + (v - prev) * .07; prev = v; v *= 4; }
        else if (mode === 3) {
          v = prev + (v - prev) * .11; prev = v; v *= 3.4;
          const u = i / n;
          if (u < .16) v *= u / .16;           // 늦게 피어오른다
        }
        d[i] = v;
      }
    }
    _imp[type] = b;
    return b;
  }

  /* 그레인 엔진 — 링버퍼에서 조각을 붙잡는 워크릿.
     모드: mosaic(조각 하나를 붙잡아 되풂) · sequence(되풀며 아르페지오)
           glitch(아무 조각이나 더듬거림·역재생) · haze(긴 그레인 구름)
           tunnel(짧고 촘촘한 그레인) · strum(조각을 펼쳐 뜯는다) */
  const GRAIN_SRC = `
class SoriGrain extends AudioWorkletProcessor {
  constructor() {
    super();
    this.B = new Float32Array(sampleRate * 4);
    this.w = 0;
    this.mode = "off"; this.div = sampleRate * .35;
    this.act = .55; this.shape = .6; this.pitches = [0, 12];
    this.grains = []; this.slice = null; this.next = 0;
    this.port.onmessage = e => {
      const m = e.data;
      if (m.mode !== undefined && m.mode !== this.mode) {
        this.mode = m.mode; this.slice = null; this.grains.length = 0;
      }
      if (m.div) this.div = Math.max(1600, Math.round(m.div * sampleRate));
      if (m.act !== undefined) this.act = m.act;
      if (m.shape !== undefined) this.shape = m.shape;
      if (m.pitches) this.pitches = m.pitches;
    };
  }
  pick() { return this.pitches[(Math.random() * this.pitches.length) | 0]; }
  spawn(pos, len, semi, pan, gain, rev, wait) {
    if (this.grains.length > 48) return;
    this.grains.push({ pos, len, t: 0, wait: wait || 0,
      rate: Math.pow(2, semi / 12) * (rev ? -1 : 1),
      pan, gain });
  }
  process(inputs, outputs) {
    const inp = inputs[0] && inputs[0][0];
    const L = outputs[0][0], R = outputs[0][1] || outputs[0][0];
    const N = L.length, B = this.B, BL = B.length;
    for (let i = 0; i < N; i++) {
      B[this.w] = inp ? inp[i] : 0;
      this.w = (this.w + 1) % BL;
    }
    if (this.mode === "off") return true;
    const div = this.div | 0, act = this.act;

    // 경계 스케줄 — 템포 격자에서 조각을 붙잡는다
    this.next -= N;
    if (this.next <= 0) {
      this.next += div;
      const start = (this.w - div + BL) % BL;
      if (this.mode === "mosaic" || this.mode === "sequence") {
        if (!this.slice || Math.random() < act)
          this.slice = { start, len: div, step: 0 };
      } else if (this.mode === "glitch") {
        if (Math.random() < act) {
          const len = (div * (.35 + Math.random() * .8)) | 0;
          const back = (Math.random() * sampleRate * 1.2) | 0;
          this.spawn((this.w - len - back + BL) % BL, len, this.pick(),
                     Math.random() * 1.6 - .8, .95, Math.random() < .4, 0);
        }
      } else if (this.mode === "strum") {
        if (Math.random() < act) {
          const steps = [0, 4, 7, 12, 16, 19, 24];
          const nvoice = 3 + ((act * 4) | 0);
          const gap = (div / (nvoice + 1)) | 0;
          for (let s = 0; s < nvoice; s++)
            this.spawn(start, (div * .8) | 0, steps[s % steps.length],
                       (s / nvoice) * 1.6 - .8, .7, false, s * gap);
        }
      }
    }
    // 구름 스케줄 — 확률로 흩뿌린다
    if (this.mode === "haze") {
      const rate = act * 26 / sampleRate * N;
      if (Math.random() < rate) {
        const len = (sampleRate * (.35 + Math.random() * .55)) | 0;
        const back = (Math.random() * sampleRate * 1.6) | 0;
        this.spawn((this.w - len - back + BL) % BL, len, this.pick(),
                   Math.random() * 1.8 - .9, .5, Math.random() < .15, 0);
      }
    } else if (this.mode === "tunnel") {
      const rate = act * 70 / sampleRate * N;
      if (Math.random() < rate) {
        const len = (sampleRate * (.04 + Math.random() * .07)) | 0;
        const back = (Math.random() * sampleRate * .5) | 0;
        this.spawn((this.w - len - back + BL) % BL, len,
                   this.pick() + (Math.random() * 2 - 1) * .6,
                   Math.random() * 1.8 - .9, .6, false, 0);
      }
    }
    // 마이크로루프 — 조각이 끝나면 곧바로 되풀린다
    if ((this.mode === "mosaic" || this.mode === "sequence") && this.slice
        && !this.grains.some(g => g.loop)) {
      const s = this.slice;
      let semi = this.pick();
      if (this.mode === "sequence") {
        const arp = [0, 4, 7, 12];
        semi = arp[s.step % arp.length] + (this.pitches[0] || 0);
        s.step++;
      }
      const g = { pos: s.start, len: s.len, t: 0, wait: 0,
                  rate: Math.pow(2, semi / 12), pan: (s.step % 2) * 1.2 - .6,
                  gain: .85, loop: true };
      this.grains.push(g);
    }

    // 렌더
    const fadeK = .06 + .38 * this.shape;
    for (let i = 0; i < N; i++) { L[i] = 0; R[i] = 0; }
    for (const g of this.grains) {
      const fade = Math.max(64, g.len * fadeK);
      for (let i = 0; i < N; i++) {
        if (g.wait > 0) { g.wait--; continue; }
        if (g.t >= g.len) { g.done = true; break; }
        const off = g.rate >= 0 ? g.t * g.rate : (g.len + g.t * g.rate);
        if (off < 0 || off >= g.len) { g.done = true; break; }
        const fi = (g.pos + off) % BL;
        const i0 = fi | 0, fr = fi - i0;
        const v0 = B[i0], v1 = B[(i0 + 1) % BL];
        let v = (v0 + (v1 - v0) * fr) * g.gain;
        const edge = Math.min(g.t, g.len - g.t);
        if (edge < fade) v *= edge / fade;
        const pl = .5 - g.pan * .5, pr = .5 + g.pan * .5;
        L[i] += v * pl; R[i] += v * pr;
        g.t++;
      }
      if (g.done && g.loop) g.t = 0, g.done = false;   // 되풂
    }
    this.grains = this.grains.filter(g => !g.done);
    return true;
  }
}
registerProcessor("sori-grain", SoriGrain);
`;
  const PITCH_SETS = {
    unison: [0], octave: [12], shimmer: [0, 12, 12], fifth: [0, 7],
    sub: [-12, 0], spread: [-12, 0, 7, 12],
  };

  /* 상주 이펙터 랙 — 모든 재생이 이 입구를 지나고, 조절값은 재생 중에도
     그대로 먹는다. 내려받는 WAV 는 이 랙을 지나지 않는다. */
  let RACK = null;
  function rack(c) {
    if (RACK) return RACK;
    const input = c.createGain();          // 마른 입력
    const sum = c.createGain();            // 마름 + 그레인 + 딜레이
    const out = c.createGain();
    input.connect(sum);

    // 그레인 엔진 (워크릿이 준비되면 이 사이에 끼운다)
    const grainWet = c.createGain(); grainWet.gain.value = 0;
    grainWet.connect(sum);
    let grain = null;
    if (c.audioWorklet) {
      const url = URL.createObjectURL(
        new Blob([GRAIN_SRC], { type: "application/javascript" }));
      c.audioWorklet.addModule(url).then(() => {
        grain = new AudioWorkletNode(c, "sori-grain",
          { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [2] });
        input.connect(grain); grain.connect(grainWet);
        RACK.grain = grain;
        applyFx();
      }).catch(() => {});
    }

    // 핑퐁 딜레이 — 마른 소리와 그레인을 함께 문다
    const dl = c.createDelay(2.5), dr = c.createDelay(2.5);
    const fbl = c.createGain(), fbr = c.createGain();
    const dampL = c.createBiquadFilter(); dampL.type = "lowpass";
    dampL.frequency.value = 3000;
    const dampR = c.createBiquadFilter(); dampR.type = "lowpass";
    dampR.frequency.value = 3000;
    const panL = c.createStereoPanner ? c.createStereoPanner() : c.createGain();
    const panR = c.createStereoPanner ? c.createStereoPanner() : c.createGain();
    if (panL.pan) { panL.pan.value = -.55; panR.pan.value = .55; }
    const dlyWet = c.createGain();
    input.connect(dl); grainWet.connect(dl);
    dl.connect(dampL); dampL.connect(fbl); fbl.connect(dr);   // 좌 → 우
    dr.connect(dampR); dampR.connect(fbr); fbr.connect(dl);   // 우 → 좌
    dl.connect(panL); dr.connect(panR);
    panL.connect(dlyWet); panR.connect(dlyWet); dlyWet.connect(sum);

    // 공명 필터 + 변조 — 모든 것이 이 문을 지난다
    const filt = c.createBiquadFilter(); filt.type = "lowpass";
    filt.frequency.value = 5200; filt.Q.value = .8;
    const lfo = c.createOscillator(); lfo.type = "sine";
    const lfoAmp = c.createGain(); lfoAmp.gain.value = 0;
    lfo.frequency.value = .18;
    lfo.connect(lfoAmp); lfoAmp.connect(filt.frequency); lfo.start();
    sum.connect(filt);

    // 공간 — 필터 뒤에서 젖는다
    const dryOut = c.createGain(); dryOut.gain.value = 1;
    const pre = c.createDelay(.25);
    const cv = c.createConvolver();
    const damp = c.createBiquadFilter(); damp.type = "lowpass";
    const revWet = c.createGain();
    filt.connect(dryOut); dryOut.connect(out);
    filt.connect(pre); pre.connect(cv); cv.connect(damp);
    damp.connect(revWet); revWet.connect(out);

    // 리미터 — 그레인·공간이 겹쳐도 찌그러지지 않게
    const lim = c.createDynamicsCompressor();
    lim.threshold.value = -8; lim.knee.value = 4;
    lim.ratio.value = 14; lim.attack.value = .002; lim.release.value = .18;
    const trim = c.createGain(); trim.gain.value = .8;
    out.connect(trim); trim.connect(lim);

    // 레벨미터 — 리미터 뒤(귀에 닿는 소리)를 좌우로 갈라 잰다
    const split = c.createChannelSplitter(2);
    const anL = c.createAnalyser(), anR = c.createAnalyser();
    anL.fftSize = 512; anR.fftSize = 512;
    lim.connect(split); split.connect(anL, 0); split.connect(anR, 1);

    lim.connect(c.destination);
    RACK = { input, sum, out, grain, grainWet, cv, pre, damp, revWet,
             dl, dr, fbl, fbr, dlyWet, filt, lfo, lfoAmp, anL, anR, ctx: c };
    applyFx();
    return RACK;
  }
  function applyFx() {
    if (!RACK) return;
    const F = window.__fx, c = RACK.ctx, t = c.currentTime + .02;
    const beat = 60 / (F.tempo || 72);
    // 그레인
    const gOn = F.prog && F.prog !== "off";
    RACK.grainWet.gain.setTargetAtTime(gOn ? F.grainMix : 0, t, .05);
    if (RACK.grain)
      RACK.grain.port.postMessage({
        mode: gOn ? F.prog : "off",
        div: Math.min(2.2, beat * (F.grainDiv || .5)),
        act: F.activity, shape: F.shape,
        pitches: PITCH_SETS[F.pitchSet] || [0],
      });
    // 딜레이
    const on = F.dlyDiv > 0;
    const dt = Math.min(2.4, beat * (on ? F.dlyDiv : .5));
    RACK.dl.delayTime.setTargetAtTime(dt, t, .05);
    RACK.dr.delayTime.setTargetAtTime(dt, t, .05);
    RACK.fbl.gain.setTargetAtTime(on ? Math.min(.72, F.dlyFb) : 0, t, .05);
    RACK.fbr.gain.setTargetAtTime(on ? Math.min(.72, F.dlyFb) : 0, t, .05);
    RACK.dlyWet.gain.setTargetAtTime(on ? F.dlyMix : 0, t, .05);
    // 필터 + 변조
    RACK.filt.frequency.setTargetAtTime(F.cut || 5200, t, .05);
    RACK.filt.Q.setTargetAtTime(.5 + (F.res || 0) * 11, t, .05);
    RACK.lfo.frequency.setTargetAtTime(Math.max(.02, F.modRate || .18), t, .05);
    RACK.lfoAmp.gain.setTargetAtTime((F.modDepth || 0) * (F.cut || 5200) * .55,
                                     t, .05);
    // 공간
    const rev = F.revType && F.revType !== "off";
    if (rev) RACK.cv.buffer = impulse(c, F.revType);
    RACK.revWet.gain.setTargetAtTime(rev ? F.revMix : 0, t, .05);
    RACK.pre.delayTime.setTargetAtTime(F.preDelay || 0, t, .05);
    RACK.damp.frequency.setTargetAtTime(F.tone || 4200, t, .05);
  }
  /* 레벨 — 좌·우 RMS 와 피크 [0..1]. 미터가 매 프레임 부른다. */
  const _mBuf = new Float32Array(512);
  function meterLevel() {
    if (!RACK) return null;
    const read = an => {
      an.getFloatTimeDomainData(_mBuf);
      let s = 0, pk = 0;
      for (let i = 0; i < _mBuf.length; i++) {
        const v = _mBuf[i]; s += v * v;
        const a = Math.abs(v); if (a > pk) pk = a;
      }
      return [Math.sqrt(s / _mBuf.length), pk];
    };
    const [rl, pl] = read(RACK.anL), [rr, pr] = read(RACK.anR);
    return { l: rl, r: rr, pl, pr };
  }
  function fxInput(c) {
    return { input: rack(c).input };
  }
  function playBuffer(pcm, sr, onEnd) {
    const c = audio();
    const buf = c.createBuffer(1, pcm.length, sr);
    const ch = buf.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) ch[i] = pcm[i] / 32768;
    const src = c.createBufferSource();
    src.buffer = buf;
    src.loop = !!window.__fx.loop;      // 루퍼
    const fx = fxInput(c);
    src.connect(fx.input);
    if (!src.loop) src.onended = onEnd;
    src.start();
    return { src, tap: fx.analyserTap, ctx: c };
  }
  const at = (v, root) => v.map(x => root + x);

  /* ══ 1. 이론 — 수치와 소리로 ══ */
  const SCALE_KO = { major: "장음계", minor: "자연단음계", neutral: "온음계" };
  function playMelody(pitches, step = .32, dur = .3, vel = 96) {
    pitches.forEach((p, i) =>
      setTimeout(() => playChord([p], dur, vel), i * step * 1000));
  }
  function renderTheory() {
    const box = $("#theoryBody");
    if (!box) return;

    // 종지 하행의 거칢 사다리
    const svg = sv("svg", { viewBox: "0 0 640 200", class: "roll",
                            style: "min-width:520px" });
    const X = t => 80 + t * 100, Y = d => 172 - d * 140;
    for (let t = 0; t < 6; t++) {
      svg.appendChild(sv("line", { x1: X(t), x2: X(t), y1: 28, y2: 172,
        stroke: "#222a34", "stroke-width": .5 }));
      const tx = sv("text", { x: X(t), y: 190, fill: "#67788c",
        "font-size": "11", "text-anchor": "middle" });
      tx.textContent = `${t}등급 +${K.tierLeap[t]}`;
      svg.appendChild(tx);
    }
    let path = "";
    D.theory.leapRoughness.forEach((d, t) => {
      path += (t ? "L" : "M") + X(t) + " " + Y(d);
    });
    svg.appendChild(sv("path", { d: path, fill: "none",
      stroke: "#e9b44c", "stroke-width": 1.6 }));
    D.theory.leapRoughness.forEach((d, t) => {
      const c = sv("circle", { cx: X(t), cy: Y(d), r: 5, fill: "#e9b44c",
        style: "cursor:pointer" });
      c.addEventListener("click", () => {
        const p1 = K.melBase + K.qualitySig.major;
        playMelody([p1, p1 - K.tierLeap[t]], .4, .45);
      });
      const ti = document.createElementNS(NS, "title");
      ti.textContent = `${t}등급 — 종지 하행 −${K.tierLeap[t]}반음, 거칢 ${d}`;
      c.appendChild(ti);
      svg.appendChild(c);
    });
    const cap = sv("text", { x: 80, y: 16, fill: "#9fb0c4",
      "font-size": "11.5" });
    cap.textContent =
      "종지 하행의 거칢 — 익숙한 낱말은 부드럽게, 생소한 낱말은 튀게 (점을 누르면 그 도약이 들린다)";
    svg.appendChild(cap);
    box.appendChild(svg);

    // 세 음계
    const scaleRow = el("div", { class: "quad" });
    for (const q of Q_NAME) {
      const cell = el("div", { class: "quadcell" });
      cell.style.borderColor = COLOR[q];
      cell.appendChild(el("div", { class: "quadhead" })).appendChild(
        el("b", null, `${Q_KO[q]} — ${SCALE_KO[q]}`));
      cell.appendChild(el("div", { class: "mono dim",
        style: "font-size:.72rem" },
        "서명 +" + K.qualitySig[q] + " · 음계 " + K.scale[q].join(" ")));
      const b = el("button", { class: "chip", type: "button" }, "♪ 음계 듣기");
      b.addEventListener("click", () =>
        playMelody(K.scale[q].slice(0, 8).map(o => K.melBase + o), .22, .2));
      cell.appendChild(b);
      scaleRow.appendChild(cell);
    }
    box.appendChild(scaleRow);

    // 사분면 — 실제 낱말의 멜로디
    const grid = el("div", { class: "quad" });
    const quads = [["흔함×장", "major", 0], ["흔함×단", "minor", 0],
                   ["드묾×장", "major", 5], ["드묾×단", "minor", 5]];
    for (const [label, q, tRep] of quads) {
      const cell = el("div", { class: "quadcell" });
      cell.style.borderColor = COLOR[q];
      const h = el("div", { class: "quadhead" });
      h.appendChild(el("b", null, label));
      cell.appendChild(h);
      const words = (D.theory.quadrants.ko[label] || []);
      cell.appendChild(el("div", { class: "dim", style: "font-size:.85rem" },
        words.slice(0, 4).map(w => w[0]).join(" · ")));
      const wordsEn = (D.theory.quadrants.en[label] || []);
      cell.appendChild(el("div", { class: "dim mono",
        style: "font-size:.72rem" },
        wordsEn.slice(0, 3).map(w => w[0]).join(" · ")));
      const b = el("button", { class: "chip", type: "button" },
        "♪ " + (words[0] ? words[0][0] : "") + " 의 멜로디");
      b.addEventListener("click", () => {
        if (!words[0]) return;
        const [form, tag, tier, qi] = words[0];
        const e = W.entryOf("ko", form, tag);
        if (!e) return;
        const ev = W.encodeGlyph(3, 1, "ko", e[0], e[1], e[2], 1, 0, e[3]);
        const mel = ev.filter(x => x.p.length === 1).map(x => x.p[0]);
        playMelody(mel, .3, .28);
      });
      cell.appendChild(b);
      grid.appendChild(cell);
    }
    box.appendChild(grid);
  }

  /* ══ 2. 전체 사전 검색 ══ */
  const FULL = { ko: null, en: null };
  async function loadFull(lang) {
    if (FULL[lang]) return FULL[lang];
    const res = await fetch("dict/" + lang + ".tsv.gz");
    if (!res.ok) throw new Error("사전을 내려받지 못했다");
    const ds = new DecompressionStream("gzip");
    const text = await new Response(res.body.pipeThrough(ds)).text();
    FULL[lang] = text.split("\n").slice(1).filter(Boolean);
    return FULL[lang];
  }
  async function searchFull(qraw) {
    const out = $("#dictHits");
    out.textContent = "";
    const q = qraw.trim();
    if (!q) return;
    const lang = /[가-힣ᄀ-ᇿ]/.test(q) ? "ko" : "en";
    out.appendChild(el("p", { class: "dim" },
      FULL[lang] ? "찾는 중 …" : "사전을 처음 여는 중 … (한 번만 내려받는다)"));
    let lines;
    try { lines = await loadFull(lang); }
    catch (e) { out.textContent = ""; out.appendChild(
      el("p", { class: "err" }, e.message)); return; }
    const needle = q.toLowerCase();
    const exact = [], prefix = [];
    for (const line of lines) {
      const i = line.indexOf("\t");
      const form = line.slice(0, i);
      const f = lang === "en" ? form : form;
      if (f === needle || form === q) exact.push(line);
      else if (form.startsWith(q) || f.startsWith(needle)) {
        if (prefix.length < 400) prefix.push(line);
      }
    }
    const rows = exact.concat(prefix)
      .map(l => l.split("\t"))
      .sort((a, b) => (+b[2]) - (+a[2]))
      .slice(0, 30);
    out.textContent = "";
    out.appendChild(el("p", { class: "dim", style: "font-size:.82rem" },
      `${lang} 사전 ${lines.length.toLocaleString()}항목에서 `
      + `${(exact.length + prefix.length).toLocaleString()}개 일치 — 앞의 ${rows.length}개`));
    for (const r of rows) {
      const [form, tag, freq, rank, tier, pol, qual, idx] = r;
      const row = el("div", { class: "hit hit4" });
      const c1 = el("div");
      c1.appendChild(el("b", null, form));
      c1.appendChild(el("span", { class: "mono dim" }, " /" + tag));
      row.appendChild(c1);
      const ci = W.approxOf(lang, form, tag);
      const isC = W.isConcept(lang, form, tag);
      row.appendChild(el("div", { class: "dim", style: "font-size:.82rem" },
        `${K.tierLabel[+tier]} · ${Q_KO[qual]}`
        + (pol !== "0" ? ` ${+pol > 0 ? "+" : ""}${pol}` : "")
        + ` · 빈도 ${(+freq).toLocaleString()}`));
      row.appendChild(el("div", { class: "dim mono", style: "font-size:.75rem" },
        isC ? `≡ ${D.concepts[ci][0]}↔${D.concepts[ci][2]}`
        : ci != null ? `≈ ${D.concepts[ci][0]}↔${D.concepts[ci][2]}`
        : lang + " 전용"));
      const b = el("button", { class: "chip", type: "button" }, "♪ 미리보기");
      b.addEventListener("click", () => {
        // 주어 자리에 놓았을 때의 글리프 — 구조 화음은 낮고 길게,
        // 멜로디는 또렷하게.
        const qi = { major:0, minor:1, neutral:2 }[qual];
        const ev = W.encodeGlyph(3, isC ? 0 : 1, isC ? null : lang,
                                 +tier, qi, isC ? ci : +idx, 1, 0, +pol);
        let t = 0;
        for (const e of ev) {
          const mel = e.p.length === 1;
          setTimeout(((ps, dd) => () =>
            playChord(ps, dd, mel ? 100 : 66))(e.p, mel ? .34 : .5), t);
          t += mel ? 300 : 420;
        }
      });
      row.appendChild(b);
      out.appendChild(row);
    }
  }

  /* ══ 3. 안내형 음 입력 ══ */
  const seq = [];       // 화음의 차례
  let picked = [];      // 지금 고르는 화음

  function expectation(chords) {
    const T = R.tables;
    let i = 0, state = "start", run = [], tonic = null;
    const cadence = () => {
      if (run.length < 3) return false;
      const q = T.QUAL_BY_SIG[run[run.length - 2] - tonic];
      return q !== undefined && T.TIER_BY_LEAP[
        run[run.length - 2] - run[run.length - 1]] !== undefined;
    };
    while (i < chords.length) {
      const c = [...chords[i]].sort((x, y) => x - y);
      if (state === "start") {
        if (R.readTerm(c) !== undefined) { i++; continue; }
        if (!R.isStart(c) || c.length !== 3
            || T.ROLE_BY_INNER[c[1] - K.pedal] === undefined)
          return { state: "오류",
            hint: `${i + 1}번째 — 낱말은 머리(베이스 C3 + 역할 내성 + 으뜸음)로 시작한다` };
        tonic = c[2]; state = "mel"; run = []; i++; continue;
      }
      // state === "mel"
      if (R.isStart(c) || R.readTerm(c) !== undefined) {
        if (!cadence()) return { state: "오류",
          hint: "종지 두 음(3도 → 하행 도약)이 어긋난다" };
        state = "start"; continue;      // 이 화음을 머리로 다시 읽는다
      }
      if (c.length > 1) {
        // 표지 내성을 거느린 종지1 — 꼭대기가 멜로디다
        const ok = c[c.length - 1] > 56
          && c.slice(0, -1).every(m =>
               T.KIND_BY_MARK[m] !== undefined
               || m === K.flagMark || m === K.joinMark);
        if (!ok) return { state: "오류",
          hint: `${i + 1}번째 — 내성은 표지(49~56)만 설 수 있다` };
      }
      run.push(c[c.length - 1]); i++; continue;
    }
    if (state === "start" || tonic == null) return { state: "start" };
    const sigPending = run.length >= 1
      && T.QUAL_BY_SIG[run[run.length - 1] - tonic] !== undefined;
    return { state: "mel", run, tonic, cadenceOk: cadence(), sigPending,
             sig1: run.length ? run[run.length - 1] : null };
  }

  function candidates(exp) {
    const out = [];
    if (exp.state === "오류") return out;
    if (exp.state === "start") {
      // 머리: 베이스 C3 + 역할 내성 + 으뜸음. 으뜸음은 낱말이 정한다 —
      // 다섯 으뜸음이 모두 문이 된다.
      K.roles.forEach((r, i) => out.push({
        label: r, cls: "marker",
        p: [K.pedal, K.pedal + K.roleInner[i], K.tonics[0]],
        alt: K.tonics.map(t => [K.pedal, K.pedal + K.roleInner[i], t]) }));
      K.terminators.forEach(t => out.push({
        label: "종결 " + t, cls: "marker", p: [...K.termSet[t]] }));
      return out;
    }
    const tonic = exp.tonic;
    if (exp.sigPending)
      K.tierLeap.forEach((leap, t) => out.push({
        label: `${t}등급 하행 (−${leap})`, cls: "marker",
        p: [exp.sig1 - leap] }));
    // 자릿음 — 으뜸음 위 계단 (종지가 성질을 확정한다)
    for (const q of Q_NAME)
      K.scale[q].forEach((off, deg) => {
        const d = K.digitOrder[q].indexOf(deg);
        out.push({ label: Q_KO[q] + "·" + d, cls: q, p: [tonic + off] });
      });
    for (const q of Q_NAME)
      out.push({ label: "종지 " + Q_KO[q], cls: q,
        p: [tonic + K.qualitySig[q]] });
    if (exp.run.length >= 1) {
      // 표지 내성을 거느린 종지1 — 낱말 갈래·이음은 여기 함께 울린다
      for (const [kl, m] of Object.entries(K.kindMark)) {
        const [kn, lg] = kl.split("|");
        out.push({ label: (kn === "WORD" ? lg + " 전용" : lg + " 글자")
                     + " 종지장", cls: "marker",
          p: [m, tonic + K.qualitySig.major] });
      }
      out.push({ label: "이음 종지장 (낱말 계속)", cls: "marker",
        p: [K.joinMark, tonic + K.qualitySig.major] });
    }
    if (exp.cadenceOk) {
      K.roles.forEach((r, i) => out.push({
        label: "다음 낱말 · " + r, cls: "marker",
        p: [K.pedal, K.pedal + K.roleInner[i], K.tonics[0]] }));
      K.terminators.forEach(t => out.push({
        label: "종결 " + t, cls: "marker", p: [...K.termSet[t]] }));
    }
    return out;
  }

  function drawKeys() {
    const host = $("#keys");
    host.textContent = "";
    for (let m = K.lowest; m <= K.highest; m++) {
      const black = [1, 3, 6, 8, 10].includes(m % 12);
      const k = el("button", { class: "key" + (black ? " black" : "")
        + (picked.includes(m) ? " on" : ""), type: "button" });
      k.appendChild(el("span", null, nm(m)));
      k.addEventListener("click", () => {
        if (picked.includes(m)) picked = picked.filter(x => x !== m);
        else if (picked.length < 3) picked.push(m);
        playChord([m], .3, 70);
        drawKeys();
      });
      host.appendChild(k);
    }
    $("#pickShow").textContent = picked.length
      ? picked.sort((a, b) => a - b).map(nm).join(" + ") : "—";
  }

  let pianoBound = false;
  function refreshPiano() {
    if (!pianoBound) {
      pianoBound = true;
      $("#addChord").addEventListener("click", () => {
        if (!picked.length) return;
        seq.push([...picked].sort((a, b) => a - b));
        playChord(picked, .45);
        picked = [];
        refreshPiano();
      });
      $("#undoChord").addEventListener("click", () => {
        seq.pop(); refreshPiano();
      });
      $("#clearChord").addEventListener("click", () => {
        seq.length = 0; picked = []; refreshPiano();
      });
    }
    drawKeys();
    // 지금까지의 차례
    const chipbox = $("#seqShow");
    chipbox.textContent = "";
    seq.forEach((ch, i) => {
      const c = el("span", { class: "seqchip mono" }, ch.map(nm).join("+"));
      c.addEventListener("click", () => playChord(ch, .5));
      chipbox.appendChild(c);
    });
    // 상태와 후보
    const exp = expectation(seq);
    const stName = exp.state === "role" ? "역할 화음 (또는 종결)"
      : exp.state === "오류" ? "오류"
      : exp.sigPending ? "등급 도약 — 종지를 맺는다"
      : exp.cadenceOk ? "자릿음 계속, 또는 이음/다음 낱말"
      : "자릿음, 또는 종지 시작";
    $("#pianoState").textContent =
      seq.length ? `다음에 올 것: ${stName}` : "역할 화음부터 시작한다";
    if (exp.state === "오류") $("#pianoState").textContent = "⚠ " + exp.hint;
    const cbox = $("#candBox");
    cbox.textContent = "";
    for (const c of candidates(exp)) {
      const b = el("button", { class: "cand " + c.cls, type: "button" },
        c.label);
      const ti = c.p.map(nm).join("+");
      b.title = ti;
      b.addEventListener("click", () => {
        seq.push(c.p); playChord(c.p, .45); refreshPiano(); liveDecode();
      });
      cbox.appendChild(b);
    }
    liveDecode();
  }

  const fedFull = new Set();
  function liveDecode() {
    const out = $("#pianoOut");
    if (!seq.length) { out.textContent = ""; return; }
    const readings = R.readAll(seq);
    const miss = R.unresolvedLangs(readings).filter(l => !fedFull.has(l));
    if (miss.length) {
      miss.forEach(l => fedFull.add(l));
      Promise.all(miss.map(l =>
        loadFull(l).then(ls => window.SoriWrite.feedFull(l, ls))))
        .then(() => liveDecode()).catch(() => {});
    }
    const parts = [];
    for (const r of readings) {
      const langs = new Set();
      for (const it of r.items) if (it.lang) langs.add(it.lang);
      const src = langs.size === 1 ? [...langs][0] : null;
      const ko = src === "ko" ? R.toSame(r.items, r.terminator, "ko")
        : R.toKorean(R.crossItems(r.items), r.terminator);
      const en = src === "en" ? R.toSame(r.items, r.terminator, "en")
        : R.toEnglish(R.crossItems(r.items), r.terminator);
      if (ko || en) parts.push(`${ko || "—"}  ·  ${en || "—"}`);
      for (const it of r.items) if (it.kind === "개념")
        parts.push(`  ${it.c[0]} ↔ ${it.c[2]}  (${K.roles[it.role]})`);
    }
    out.textContent = parts.length ? parts.join("\n")
      : "(아직 낱말이 완성되지 않았다 — 맺음 화음까지 넣으면 읽힌다)";
  }

  /* ══ 4. 시각화 — 30초 기계적 예술 ══ */
  const SLOT_RULE = {
    "으뜸": "낱말의 머리 — 으뜸음이 조를 열고, 베이스 C3 위 내성이 역할이다",
    "종지": "멜로디의 맺음 — 3도가 감정을, 하행 도약이 익숙함을",
    "이름": "멜로디 자릿음 — 음계 계단이 진법 한 자리",
    "종결": "멜로디 없는 저음 이중음 — 문장의 끝",
  };
  let cine = { raf: null, src: null, stop: null };

  function digitsOf32(index, base) {
    const out = []; let m = index + 1;
    while (m > 0) { const r = m % base || base; out.push(r - 1);
      m = (m - r) / base; }
    return out.reverse();
  }

  function openCinema(piece, tempo, auto) {
    const host = $("#cinema");
    host.hidden = false;
    if (cine.raf) cancelAnimationFrame(cine.raf);
    if (cine.src) { try { cine.src.stop(); } catch (e) {} cine.src = null; }
    cine = { raf: null, src: null };
    tempo = tempo || 72;
    const sched = W.schedule(piece.notes, tempo);
    const total = sched[sched.length - 1][0] + sched[sched.length - 1][1] + .3;

    /* ── 문장 — 크게, 아래쪽에 ── */
    const wordsBox = $("#cnWords");
    wordsBox.textContent = "";
    const wordEls = [];
    piece.sentences.forEach((sn, si) => {
      sn.analysis.forEach((a, wi) => {
        const w = el("span", { class: "cnword" }, a.surface);
        wordsBox.appendChild(w);
        wordEls.push({ si, wi, el: w });
      });
      wordsBox.appendChild(el("span", { class: "cnword end" }, sn.term));
    });

    /* ── 낱말 구성 띠 — 재생 전에 짜임을 미리 보이고,
          음영으로 지금 어느 조각이 울리는지 말한다 ── */
    const segBox = $("#cnSeg");
    // 음표 → (낱말, 낱말 안 순번) 미리 계산
    const noteMeta = [];
    {
      let prevKey = null, segIdx = 0;
      sched.forEach(([, , n], k) => {
        const wkey = n.si + "/" + n.w;
        if (wkey !== prevKey) { prevKey = wkey; segIdx = 0; }
        noteMeta.push({ wkey, segIdx });
        segIdx++;
      });
    }
    let segKey = null, segEls = [];
    function buildSeg(i) {
      const [, , n] = sched[i];
      const wkey = n.si + "/" + n.w;
      if (wkey === segKey) return;
      segKey = wkey;
      segBox.textContent = "";
      segEls = [];
      // 이 낱말의 모든 조각을 순서대로
      for (let k = 0; k < sched.length; k++) {
        const m = sched[k][2];
        if (m.si + "/" + m.w !== wkey) continue;
        const mel = m.p.length === 1;
        const q = Q_NAME[m.qi] || "neutral";
        const d = el("span", { class: "cnseg" });
        d.style.borderColor = mel ? COLOR[q] : "#4a5a6d";
        d.appendChild(el("b", null, m.slot));
        d.appendChild(el("i", null, m.p.map(nm).join("+")));
        segBox.appendChild(d);
        segEls.push({ k, el: d });
      }
    }
    function shadeSeg(i) {
      for (const s2 of segEls)
        s2.el.className = "cnseg " +
          (s2.k === i ? "now" : s2.k < i ? "done" : "todo");
    }

    /* ── 궤도 (12음 시계) ── */
    const orbit = $("#cnOrbit");
    orbit.textContent = "";
    const OC = 80;
    orbit.setAttribute("viewBox", "0 0 160 160");
    const orbDots = [];
    for (let pc = 0; pc < 12; pc++) {
      const a = pc / 12 * 2 * Math.PI - Math.PI / 2;
      const x = OC + 62 * Math.cos(a), y = OC + 62 * Math.sin(a);
      orbit.appendChild(sv("circle", { cx: x, cy: y, r: 2, fill: "#2c3745" }));
      const t = sv("text", { x: OC + 74 * Math.cos(a),
        y: OC + 74 * Math.sin(a) + 3, fill: "#43536a", "font-size": "8",
        "text-anchor": "middle", "font-family": "ui-monospace,monospace" });
      t.textContent = NAMES[pc]; orbit.appendChild(t);
      orbDots[pc] = { x, y };
    }
    const orbTrail = [];
    function orbitHit(pitches, col) {
      if (!window.__cnOrbitOn) return;
      for (const p of pitches) {
        const pc = ((p % 12) + 12) % 12;
        const { x, y } = orbDots[pc];
        if (orbTrail.length) {
          const prev = orbTrail[orbTrail.length - 1];
          const ln = sv("line", { x1: prev.x, y1: prev.y, x2: x, y2: y,
            stroke: col, "stroke-width": .8, "stroke-opacity": .5 });
          orbit.appendChild(ln); orbTrail.push({ x, y, el: ln });
        }
        const c2 = sv("circle", { cx: x, cy: y, r: 5, fill: col,
          "fill-opacity": .9 });
        orbit.appendChild(c2); orbTrail.push({ x, y, el: c2 });
        while (orbTrail.length > 26) {
          const old = orbTrail.shift();
          if (old.el) old.el.remove();
        }
      }
    }

    /* ── 타임라인 ── */
    const tl = $("#cnRoll");
    tl.textContent = "";
    const TW = 1160, TH = 150, PL = 36;
    tl.setAttribute("viewBox", `0 0 ${TW + PL + 10} ${TH + 24}`);
    const tx = t => PL + t / total * TW;
    const ty = p => 8 + (K.highest - p) * (TH - 16) / (K.highest - K.lowest);
    for (let p = K.lowest; p <= K.highest; p += 12) {
      tl.appendChild(sv("line", { x1: PL, x2: PL + TW, y1: ty(p), y2: ty(p),
        stroke: "#1d242e", "stroke-width": .7 }));
      const t = sv("text", { x: PL - 6, y: ty(p) + 3.5, fill: "#5b6b7f",
        "font-size": "9", "text-anchor": "end",
        "font-family": "ui-monospace,monospace" });
      t.textContent = nm(p); tl.appendChild(t);
    }
    const rects = [];
    sched.forEach(([t0, dur, n], i) => {
      const q = Q_NAME[n.qi];
      const col = (n.slot === "종지" || n.slot === "이름") && q
        ? COLOR[q] : "#3d4b5c";
      for (const p of n.p) {
        const r = sv("rect", { x: tx(t0), y: ty(p) - 2.6,
          width: Math.max(2, tx(t0 + dur) - tx(t0) - 1.2), height: 5.2,
          rx: 1, fill: col, "fill-opacity": .25 });
        tl.appendChild(r);
        rects.push({ i, el: r });
      }
    });
    const head = sv("line", { x1: PL, x2: PL, y1: 4, y2: TH + 6,
      stroke: "#e9b44c", "stroke-width": 1.2 });
    tl.appendChild(head);

    /* ── 매트릭스 — 성질 × 등급의 자리 위에서 문장이 움직인다 ── */
    const mx = $("#cnMatrix");
    mx.textContent = "";
    const mxCells = {};
    const mxHead = el("div", { class: "mxrow mxhead" });
    mxHead.appendChild(el("span", { class: "mxlab" }, ""));
    for (let t = 0; t < 6; t++)
      mxHead.appendChild(el("span", { class: "mxlab" },
        t === 0 ? "익숙 0" : t === 5 ? "생소 5" : String(t)));
    mx.appendChild(mxHead);
    for (const q of Q_NAME) {
      const row = el("div", { class: "mxrow" });
      const lab = el("span", { class: "mxlab" }, Q_KO[q]);
      lab.style.color = COLOR[q];
      row.appendChild(lab);
      for (let t = 0; t < 6; t++) {
        const cell = el("div", { class: "mxcell" });
        cell.style.borderColor = COLOR[q] + "44";
        row.appendChild(cell);
        mxCells[q + "/" + t] = cell;
      }
      mx.appendChild(row);
    }
    // 낱말을 제 칸에 미리 놓는다 — 글리프가 등급·성질을 직접 안다
    const mxWordEls = {};
    piece.sentences.forEach((sn, si) => {
      const seen = new Set();
      for (const g of sn.glyphs) {
        const wkey = si + "/" + g.word;
        if (g.word < 0 || seen.has(wkey)) continue;
        seen.add(wkey);
        const q = Q_NAME[g.qi] || "neutral";
        const t2 = Math.max(0, Math.min(5, g.tier ?? 0));
        const cell = mxCells[q + "/" + t2];
        if (!cell) continue;
        const w = el("span", { class: "mxword" },
          (sn.analysis[g.word] && sn.analysis[g.word].surface)
          || g.label.split("/")[0]);
        cell.appendChild(w);
        mxWordEls[wkey] = { el: w, col: COLOR[q] };
      }
    });
    function matrixHit(n) {
      const wkey = n.si + "/" + n.w;
      for (const k in mxWordEls) {
        const on = k === wkey;
        mxWordEls[k].el.classList.toggle("on", on);
        if (on) mxWordEls[k].el.style.color = mxWordEls[k].col;
        else if (!mxWordEls[k].el.classList.contains("was"))
          mxWordEls[k].el.style.color = "";
      }
      if (mxWordEls[wkey]) mxWordEls[wkey].el.classList.add("was");
    }
    function applyMatrixMode() {
      const on = !!window.__cnMatrixOn;
      $("#cnStage").style.display = on ? "none" : "";
      $("#cnRoll").style.display = on ? "none" : "";
      $("#cnSeg").style.display = on ? "none" : "";
      mx.hidden = !on;
    }
    applyMatrixMode();
    cine.applyMatrixMode = applyMatrixMode;

    /* ── 조립대 ── */
    const asm = $("#cnAsm");
    const AW = 560, AH = 150;
    asm.setAttribute("viewBox", `0 0 ${AW} ${AH}`);
    let trail = [], trailKey = null;
    function drawAsm(n, frac) {
      asm.textContent = "";
      for (let p = K.lowest; p <= K.highest; p++) {
        const y = 10 + (K.highest - p) * (AH - 22) / 24;
        asm.appendChild(sv("line", { x1: 300, x2: p % 12 === 0 ? 545 : 535,
          y1: y, y2: y, stroke: p % 12 === 0 ? "#2c3745" : "#1b232d",
          "stroke-width": p % 12 === 0 ? 1 : .5 }));
        if (p % 12 === 0) {
          const t = sv("text", { x: 552, y: y + 3, fill: "#5b6b7f",
            "font-size": "9", "font-family": "ui-monospace,monospace" });
          t.textContent = nm(p); asm.appendChild(t);
        }
      }
      if (!n) return;
      const put = (x, y, txt, size, color, weight) => {
        const t = sv("text", { x, y, fill: color || "#c8d4e2",
          "font-size": size || 12 });
        if (weight) t.setAttribute("font-weight", weight);
        t.textContent = txt; asm.appendChild(t);
      };
      const q = Q_NAME[n.qi] || "neutral";
      const isMel = n.slot === "종지" || n.slot === "이름";
      const col = isMel ? COLOR[q] : "#8fa3b8";
      put(6, 24, n.src, 14, "#e6edf5", "600");
      put(6, 44, n.slot + " — " + (SLOT_RULE[n.slot] || ""), 10, "#67788c");
      let desc = "";
      if (n.slot === "종지") {
        const off = n.p[n.p.length - 1] - tonicOfNote(n);
        desc = { 4: "종지 = 장 (장3도)", 3: "종지 = 단 (단3도)",
                 6: "종지 = 중성 (삼전음)" }[off]
          || "종지 하행 — 거칢이 익숙함을 말한다";
      } else if (n.slot === "이름") desc = Q_KO[q] + " 음계 · 지그재그 계단";
      else if (n.slot === "으뜸")
        desc = n.role + " — 베이스 위 +"
          + (n.p.length >= 2 ? n.p[1] - n.p[0] : "?") + "반음";
      put(6, 66, desc, 10.5, "#9fb0c4");
      if (n.idx !== undefined && (n.kind === 0 || n.kind === 1))
        put(6, 84, "#" + n.idx, 10, "#67788c");
      put(6, 128, n.p.map(nm).join(" + "), 13, col, "600");

      const wkey = n.si + "/" + n.w;
      if (wkey !== trailKey) { trail = []; trailKey = wkey; }
      if (isMel && (!trail.length
          || trail[trail.length - 1].p !== n.p[0])) {
        trail.push({ p: n.p[0], slot: n.slot });
        if (trail.length > 10) trail.shift();
      }
      const yOf = p => 10 + (K.highest - p) * (AH - 22) / 24;
      let prev = null;
      trail.forEach((tn, i2) => {
        const x = 310 + i2 * 22, y = yOf(tn.p);
        if (prev)
          asm.appendChild(sv("line", { x1: prev[0], y1: prev[1],
            x2: x, y2: y, stroke: col, "stroke-width": 1,
            "stroke-opacity": .6 }));
        const last = i2 === trail.length - 1;
        asm.appendChild(sv("circle", { cx: x, cy: y,
          r: last ? 6.5 - 2.5 * Math.min(1, frac || 0) : 3.2,
          fill: tn.slot === "종지" ? col : "none",
          stroke: col, "stroke-width": 1.3 }));
        prev = [x, y];
      });
      if (!isMel)
        for (const p of n.p) {
          const y = yOf(p);
          asm.appendChild(sv("rect", { x: 310, y: y - 2.5,
            width: 90 + 120 * Math.max(0, 1 - (frac || 0)), height: 5,
            fill: "#4a5a6d", "fill-opacity": .8 }));
        }
    }
    drawAsm(null);

    /* ── 트랜스포트 — 재생·정지·반복. 끝나도 창은 남는다 ── */
    const c = audio();
    const pcm = W.synth(piece.notes, tempo);
    const buf = c.createBuffer(1, pcm.length, W.SR);
    const chd = buf.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) chd[i] = pcm[i] / 32768;

    let playing = false, offset = 0, startPerf = 0, cur = -1;
    function startFrom(off) {
      stopSrc();
      const srcN = c.createBufferSource();
      srcN.buffer = buf;
      srcN.connect(fxInput(c).input);
      srcN.start(0, Math.min(off, buf.duration - .01));
      cine.src = srcN;
      offset = off;
      startPerf = performance.now() / 1000;
      playing = true;
      $("#cnPlay").textContent = "⏸";
    }
    function stopSrc() {
      if (cine.src) { try { cine.src.stop(); } catch (e) {} cine.src = null; }
    }
    function pause() {
      if (!playing) return;
      offset = getT(); stopSrc(); playing = false;
      $("#cnPlay").textContent = "▶";
    }
    const getT = () => playing
      ? offset + (performance.now() / 1000 - startPerf) : offset;
    cine.toggle = () => {
      if (playing) pause();
      else startFrom(getT() >= total - .05 ? 0 : getT());
    };

    function frame() {
      const t = Math.min(total, getT());
      $("#cnClock").textContent = t.toFixed(1) + " / " + total.toFixed(1) + " s";
      head.setAttribute("x1", tx(t)); head.setAttribute("x2", tx(t));
      let i = -1;
      while (i + 1 < sched.length && sched[i + 1][0] <= t) i++;
      if (i >= 0) {
        const [st, du, n] = sched[i];
        const frac = Math.max(0, Math.min(1, (t - st) / du));
        if (!window.__cnMatrixOn) { buildSeg(i); shadeSeg(i); drawAsm(n, frac); }
        if (i !== cur) {
          cur = i;
          const isMel = n.slot === "종지" || n.slot === "이름";
          orbitHit(n.p, isMel ? COLOR[Q_NAME[n.qi] || "neutral"] : "#4a5a6d");
          matrixHit(n);
          for (const r of rects)
            r.el.setAttribute("fill-opacity",
              r.i === i ? .95
              : r.i < i ? (window.__cnTrailOn ? .5 : .25) : .25);
          // 낱말은 제 글리프가 우는 동안 내내 크게
          wordEls.forEach(w => w.el.classList.toggle("on",
            w.si === n.si && w.wi === n.w));
        }
      }
      if (playing && getT() >= total) {
        if (window.__fx.loop) { cur = -1; startFrom(0); }
        else pause();                 // 끝 — 창은 닫지 않는다
      }
      cine.raf = requestAnimationFrame(frame);
    }
    if (auto) startFrom(0);
    else { drawAsm(sched[0] && sched[0][2], 0); buildSeg(0); shadeSeg(-1);
           $("#cnPlay").textContent = "▶"; }
    cine.raf = requestAnimationFrame(frame);
  }
  function closeCinema() {
    if (cine.raf) cancelAnimationFrame(cine.raf);
    if (cine.src) { try { cine.src.stop(); } catch (e) {} }
    cine = { raf: null, src: null };
    $("#cinema").hidden = true;
  }

  window.__cnTrailOn = true;
  window.__cnOrbitOn = true;
  window.__cnMatrixOn = false;

  window.SoriStudio = { renderTheory, searchFull, refreshPiano, loadFull,
                        openCinema, closeCinema, playChord, playMelody,
                        playBuffer, fxInput, applyFx, meterLevel,
                        cineToggle: () => cine.toggle && cine.toggle(),
                        cineMatrix: () => cine.applyMatrixMode
                          && cine.applyMatrixMode(),
                        expectation, candidates };
})();
