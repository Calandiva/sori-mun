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
     공간계 위주의 단순한 세팅: 홑음 멜로디도 아름답게 울리도록. */
  window.__fx = { space: true, echo: false, loop: false };
  let _impulse = null;
  function impulse(c) {
    if (_impulse) return _impulse;
    const n = c.sampleRate * 2.6;
    const b = c.createBuffer(2, n, c.sampleRate);
    for (let ch = 0; ch < 2; ch++) {
      const d = b.getChannelData(ch);
      for (let i = 0; i < n; i++)
        d[i] = (Math.random() * 2 - 1) * Math.pow(1 - i / n, 2.6);
    }
    _impulse = b;
    return b;
  }
  function fxInput(c) {
    // 설정에 맞는 입력 노드를 만든다. destination 까지 이어져 있다.
    const inp = c.createGain(), out = c.createGain();
    const dry = c.createGain();
    dry.gain.value = 1;
    inp.connect(dry); dry.connect(out);
    if (window.__fx.echo) {
      const d = c.createDelay(1.5); d.delayTime.value = .34;
      const fb = c.createGain(); fb.gain.value = .36;
      const wet = c.createGain(); wet.gain.value = .30;
      inp.connect(d); d.connect(fb); fb.connect(d); d.connect(wet);
      wet.connect(out);
    }
    if (window.__fx.space) {
      const cv = c.createConvolver(); cv.buffer = impulse(c);
      const wet = c.createGain(); wet.gain.value = .45;
      inp.connect(cv); cv.connect(wet); wet.connect(out);
    }
    out.connect(c.destination);
    return { input: inp, analyserTap: out };
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

    // 서명 도약의 거칢 사다리
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
        playMelody([p1, p1 + K.tierLeap[t]], .4, .45);
      });
      const ti = document.createElementNS(NS, "title");
      ti.textContent = `${t}등급 — 서명 도약 +${K.tierLeap[t]}반음, 거칢 ${d}`;
      c.appendChild(ti);
      svg.appendChild(c);
    });
    const cap = sv("text", { x: 80, y: 16, fill: "#9fb0c4",
      "font-size": "11.5" });
    cap.textContent =
      "서명 도약의 거칢 — 익숙한 낱말은 부드럽게, 생소한 낱말은 튀게 (점을 누르면 그 도약이 들린다)";
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
    // 되읽기와 같은 걸음으로 훑어, 다음에 올 수 있는 것을 알려 준다.
    const T = R.tables;
    let i = 0, state = "role", quality = null, sig1 = null;
    while (i < chords.length) {
      const c = chords[i];
      if (state === "role") {
        if (c.length === 1) return { state: "오류",
          hint: `${i + 1}번째 — 글리프는 역할 화음으로 시작한다` };
        const k = R.key(c);
        if (T.TERM[k] !== undefined) { i++; continue; }
        if (T.ROLE[k] === undefined) return { state: "오류",
          hint: `${i + 1}번째 화음이 역할 화음이 아니다` };
        state = "head"; i++; continue;
      }
      if (state === "head") {
        if (c.length > 1) {
          const k = R.key(c);
          if (T.LANG[k] === undefined && T.LETTER[k] === undefined)
            return { state: "오류", hint: `${i + 1}번째 화음이 갈래 화음이 아니다` };
          i++; continue;
        }
        const q = T.QUAL_BY_SIG[c[0] - K.melBase];
        if (q === undefined) return { state: "오류",
          hint: `${i + 1}번째 홑음이 성질 서명이 아니다` };
        quality = q; sig1 = c[0]; state = "sig2"; i++; continue;
      }
      if (state === "sig2") {
        if (c.length !== 1 || T.TIER_BY_LEAP[c[0] - sig1] === undefined)
          return { state: "오류", hint: `${i + 1}번째 — 등급 도약이 와야 한다` };
        state = "digit"; i++; continue;
      }
      if (state === "digit") {
        if (c.length === 1) {
          if (T.DEGREE[quality][c[0] - K.melBase] === undefined)
            return { state: "오류",
              hint: `${i + 1}번째 홑음이 ${Q_KO[quality]} 음계에 없다` };
          i++; continue;
        }
        if (T.CLOSE[R.key(c)] !== undefined) { state = "role"; i++; continue; }
        return { state: "오류", hint: `${i + 1}번째 화음이 맺음이 아니다` };
      }
    }
    return { state, quality, sig1 };
  }

  function candidates(exp) {
    // 지금 상태에서 눌러 넣을 수 있는 소리들.
    const out = [];
    if (exp.state === "오류") return out;
    if (exp.state === "role") {
      K.roles.forEach((r, i) => out.push({
        label: r, cls: "marker", p: at(B.role[i], K.rolePitch[i]) }));
      K.terminators.forEach((t, i) => out.push({
        label: "종결 " + t, cls: "marker",
        p: at(B.term[i], clampRoot(B.term[i], 48)) }));
      for (const lg of ["ko", "en"]) {
        // 역할 화음 뒤에 오는 갈래 화음도 이 자리에서 이어 안내한다
      }
    } else if (exp.state === "head") {
      for (const lg of ["ko", "en"]) {
        out.push({ label: lg + " 전용", cls: "marker",
          p: at(B.language[lg], clampRoot(B.language[lg], 48)) });
        out.push({ label: lg + " 글자", cls: "marker",
          p: at(B.letter[lg], clampRoot(B.letter[lg], 48)) });
      }
      for (const q of Q_NAME)
        out.push({ label: "서명 " + Q_KO[q], cls: q,
          p: [K.melBase + K.qualitySig[q]] });
    } else if (exp.state === "sig2") {
      K.tierLeap.forEach((leap, t) => out.push({
        label: `${t}등급 (+${leap})`, cls: exp.quality,
        p: [exp.sig1 + leap] }));
    } else if (exp.state === "digit") {
      K.scale[exp.quality].forEach((off, d) => out.push({
        label: String(d), cls: exp.quality, p: [K.melBase + off] }));
      out.push({ label: "맺음·이어짐", cls: "marker",
        p: at(B.close[0], clampRoot(B.close[0], 48)) });
      out.push({ label: "맺음·끊김", cls: "marker",
        p: at(B.close[1], clampRoot(B.close[1], 48)) });
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
    const stName = { role: "역할 화음 (또는 종결)",
                     head: "갈래 화음 또는 성질 서명",
                     sig2: "등급 도약 (서명2)",
                     digit: "음계 자릿음 (또는 맺음)",
                     "오류": "오류" }[exp.state];
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

  function liveDecode() {
    const out = $("#pianoOut");
    if (!seq.length) { out.textContent = ""; return; }
    const readings = R.readAll(seq);
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
    "역할": "저음 화음 — 모양이 문장 성분을 말한다",
    "언어": "저음 화음 — 이 말에만 있는 낱말",
    "받아적기": "저음 화음 — 글자를 하나씩 적는다",
    "서명": "멜로디 서명 — 3도가 감정을, 도약이 익숙함을",
    "이름": "멜로디 자릿음 — 음계 계단이 진법 한 자리",
    "맺음": "저음 화음 — 글리프의 끝, 어절 경계",
    "종결": "저음 화음 — 문장의 끝",
  };
  let cine = { raf: null, srcNode: null };

  function digitsOf(index) {
    const out = []; let m = index + 1;
    while (m > 0) { const r = m % 32 || 32; out.push(r - 1); m = (m - r) / 32; }
    return out.reverse();
  }

  function openCinema(piece, tempo) {
    const host = $("#cinema");
    host.hidden = false;
    document.body.style.overflow = "hidden";
    tempo = tempo || 72;
    const sched = W.schedule(piece.notes, tempo);
    const total = sched[sched.length - 1][0] + sched[sched.length - 1][1];
    const notes = [...piece.notes].sort((a, b) => a.s - b.s);

    // 문장 낱말 띠
    const wordsBox = $("#cnWords");
    wordsBox.textContent = "";
    const wordEls = [];
    piece.sentences.forEach((s, si) => {
      s.analysis.forEach((a, wi) => {
        const w = el("span", { class: "cnword" }, a.surface);
        wordsBox.appendChild(w);
        wordEls.push({ si, wi, el: w });
      });
      wordsBox.appendChild(el("span", { class: "cnword dim" }, s.term));
    });

    // 아래 타임라인 (전체 화음, 시간 비례)
    const tl = $("#cnRoll");
    tl.textContent = "";
    const TW = 1160, TH = 190, PL = 36;
    tl.setAttribute("viewBox", `0 0 ${TW + PL + 10} ${TH + 26}`);
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
      const q = n.kind === 0 || n.kind === 1
        ? Q_NAME[n.qi] : null;
      const col = (n.slot === "의미" || n.slot === "자리") && q
        ? COLOR[q] : "#3d4b5c";
      for (const p of n.p) {
        const r = sv("rect", { x: tx(t0), y: ty(p) - 2.6,
          width: Math.max(2, tx(t0 + dur) - tx(t0) - 1.2), height: 5.2,
          rx: 1, fill: col, "fill-opacity": .35 });
        tl.appendChild(r);
        rects.push({ i, el: r });
      }
    });
    const head = sv("line", { x1: PL, x2: PL, y1: 4, y2: TH + 6,
      stroke: "#e9b44c", "stroke-width": 1.2 });
    tl.appendChild(head);

    // 조립대 (현재 화음)
    const asm = $("#cnAsm");
    const AW = 560, AH = 170;
    asm.setAttribute("viewBox", `0 0 ${AW} ${AH}`);
    // 현재 낱말의 멜로디를 누적해 그린다 — 궤적이 곧 이름이다
    let trail = [];      // [{p, slot}]
    let trailKey = null;
    function drawAsm(n, frac) {
      asm.textContent = "";
      for (let p = K.lowest; p <= K.highest; p++) {
        const y = 12 + (K.highest - p) * (AH - 26) / 24;
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
        t.textContent = txt; asm.appendChild(t); return t;
      };
      const q = Q_NAME[n.qi] || "neutral";
      const isMel = n.slot === "서명" || n.slot === "이름";
      const col = isMel ? COLOR[n.kind === -1 ? "neutral" : q] : "#8fa3b8";

      // 낱말 이름 — 소리 나는 동안 살짝 커진다
      const grow = 15 + 4 * Math.max(0, 1 - (frac || 0) * 2);
      put(6, 28, n.src, grow, "#e6edf5", "600");
      put(6, 50, n.slot + (isMel ? " (홑음)" : " (화음)"), 11, "#e9b44c");
      put(6, 66, SLOT_RULE[n.slot] || "", 10, "#67788c");

      // 실시간 서술 — 지금 이 소리가 무엇을 뜻하는가
      let desc = "";
      if (n.slot === "서명") {
        const off = n.p[0] - K.melBase;
        const qk = { 4: "장 (+4 장3도)", 3: "단 (+3 단3도)",
                     6: "중성 (+6 삼전음)" }[off];
        desc = qk ? "서명1 · 성질 = " + qk
          : "서명2 · 등급 도약 — 거칢이 익숙함을 말한다";
      } else if (n.slot === "이름") {
        desc = "자릿음 · " + Q_KO[q] + " 음계 위 계단";
      } else if (n.slot === "역할") {
        desc = n.role + " — 이 낱말이 문장에서 맡은 자리";
      }
      put(6, 92, desc, 10.5, "#9fb0c4");
      if (n.kind === 0 || n.kind === 1)
        put(6, 110, (n.kind === 0 ? "개념" : "낱말") + " #" + n.idx, 10, "#67788c");
      put(6, 152, n.p.map(nm).join(" + "), 13, col, "600");

      // 멜로디 궤적 — 같은 낱말 안에서 누적된다
      const wkey = n.si + "/" + n.w;
      if (wkey !== trailKey) { trail = []; trailKey = wkey; }
      if (isMel && (!trail.length || trail[trail.length - 1].p !== n.p[0]
                    || trail[trail.length - 1].i !== undefined)) {
        trail.push({ p: n.p[0], slot: n.slot });
        if (trail.length > 10) trail.shift();
      }
      const yOf = p => 12 + (K.highest - p) * (AH - 26) / 24;
      const x0 = 310, dx = 22;
      let prev = null;
      trail.forEach((tn, i2) => {
        const x = x0 + i2 * dx, y = yOf(tn.p);
        if (prev)
          asm.appendChild(sv("line", { x1: prev[0], y1: prev[1], x2: x, y2: y,
            stroke: col, "stroke-width": 1, "stroke-opacity": .6 }));
        const last = i2 === trail.length - 1;
        const r = last ? 6.5 - 2.5 * Math.min(1, frac || 0) : 3.2;
        asm.appendChild(sv("circle", { cx: x, cy: y, r,
          fill: tn.slot === "서명" ? col : "none",
          stroke: col, "stroke-width": 1.3 }));
        prev = [x, y];
      });
      // 화음(구조)은 왼쪽 낮은 자리에 겹대로
      if (!isMel)
        for (const p of n.p) {
          const y = yOf(p);
          asm.appendChild(sv("rect", { x: 310, y: y - 2.5,
            width: 90 + 120 * Math.max(0, 1 - (frac || 0)), height: 5,
            fill: "#4a5a6d", "fill-opacity": .8 }));
        }
    }
    drawAsm(null);

    // 궤도 — 12음 시계 (실험 레이어, 켜고 끌 수 있다)
    const orbit = $("#cnOrbit");
    orbit.textContent = "";
    const OC = 80;
    orbit.setAttribute("viewBox", "0 0 160 160");
    const orbDots = [];
    for (let pc = 0; pc < 12; pc++) {
      const a = pc / 12 * 2 * Math.PI - Math.PI / 2;
      const x = OC + 62 * Math.cos(a), y = OC + 62 * Math.sin(a);
      orbit.appendChild(sv("circle", { cx: x, cy: y, r: 2,
        fill: "#2c3745" }));
      const t = sv("text", { x: OC + 74 * Math.cos(a),
        y: OC + 74 * Math.sin(a) + 3, fill: "#43536a", "font-size": "8",
        "text-anchor": "middle", "font-family": "ui-monospace,monospace" });
      t.textContent = NAMES[pc]; orbit.appendChild(t);
      orbDots[pc] = { x, y };
    }
    const orbTrail = [];   // {pc, el, age}
    function orbitHit(pitches, col) {
      if (!window.__cnOrbitOn) return;
      for (const p of pitches) {
        const pc = ((p % 12) + 12) % 12;
        const { x, y } = orbDots[pc];
        if (orbTrail.length > 1) {
          const prev = orbTrail[orbTrail.length - 1];
          const ln = sv("line", { x1: prev.x, y1: prev.y, x2: x, y2: y,
            stroke: col, "stroke-width": .8, "stroke-opacity": .5 });
          orbit.appendChild(ln); orbTrail.push({ x, y, el: ln, age: 0 });
        } else orbTrail.push({ x, y, el: null, age: 0 });
        const c2 = sv("circle", { cx: x, cy: y, r: 5, fill: col,
          "fill-opacity": .9 });
        orbit.appendChild(c2); orbTrail.push({ x, y, el: c2, age: 0 });
        while (orbTrail.length > 26) {
          const old = orbTrail.shift();
          if (old.el) old.el.remove();
        }
      }
    }

    // 재생 + 동기 — 이펙터를 거친다 (내려받는 WAV 는 마른 소리 그대로)
    const pcm = W.synth(piece.notes, tempo);
    const c = audio();
    const buf = c.createBuffer(1, pcm.length, W.SR);
    const chd = buf.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) chd[i] = pcm[i] / 32768;
    const srcN = c.createBufferSource();
    srcN.buffer = buf;
    const fx = fxInput(c);
    srcN.connect(fx.input);
    const t0 = c.currentTime + .15;
    srcN.start(t0);
    cine.srcNode = srcN;
    // 소리가 막힌 환경(자동재생 차단)에서도 그림은 돌아가게 — 대체 시계
    const wall0 = performance.now() / 1000 + .15;
    let cur = -1;
    function frame() {
      const t = c.state === "running"
        ? c.currentTime - t0
        : performance.now() / 1000 - wall0;
      $("#cnClock").textContent =
        Math.max(0, t).toFixed(1) + " / " + total.toFixed(1) + " s";
      head.setAttribute("x1", tx(Math.max(0, Math.min(total, t))));
      head.setAttribute("x2", tx(Math.max(0, Math.min(total, t))));
      let i = cur;
      while (i + 1 < sched.length && sched[i + 1][0] <= t) i++;
      if (i >= 0 && i < sched.length) {
        const [st, du, n] = sched[i];
        const frac = Math.max(0, Math.min(1, (t - st) / du));
        drawAsm(n, frac);          // 매 프레임 — 크기·서술이 살아 움직인다
        if (i !== cur) {
          const isMel = n.slot === "서명" || n.slot === "이름";
          orbitHit(n.p, isMel
            ? COLOR[Q_NAME[n.qi] || "neutral"] : "#4a5a6d");
          // 잔상 — 지나간 멜로디는 제 색으로 남는다
          if (window.__cnTrailOn)
            for (const r of rects)
              if (r.i < i) r.el.setAttribute("fill-opacity", .5);
          cur = i;
          for (const r of rects)
            r.el.setAttribute("fill-opacity",
              r.i === i ? .95 : r.i < i ? .5 : .25);
          wordEls.forEach(w => w.el.classList.toggle("on",
            w.si === n.si && w.wi === n.w));
        }
      }
      if (t < total + .4) cine.raf = requestAnimationFrame(frame);
      else closeCinema();
    }
    cine.raf = requestAnimationFrame(frame);
  }
  function closeCinema() {
    if (cine.raf) cancelAnimationFrame(cine.raf);
    if (cine.srcNode) { try { cine.srcNode.stop(); } catch (e) {} }
    cine = { raf: null, srcNode: null };
    $("#cinema").hidden = true;
    document.body.style.overflow = "";
  }

  window.__cnTrailOn = true;
  window.__cnOrbitOn = true;

  window.SoriStudio = { renderTheory, searchFull, refreshPiano,
                        openCinema, closeCinema, playChord, playMelody,
                        playBuffer, fxInput,
                        expectation, candidates };
})();
