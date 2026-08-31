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
  const at = (v, root) => v.map(x => root + x);

  /* ══ 1. 이론 — 수치와 소리로 ══ */
  function renderTheory() {
    const box = $("#theoryBody");
    if (!box) return;
    // 거칢 사다리 (선 그래프)
    const svg = sv("svg", { viewBox: "0 0 640 220", class: "roll",
                            style: "min-width:520px" });
    const X = t => 70 + t * 100, Y = d => 190 - d * 140;
    for (let t = 0; t < 6; t++) {
      svg.appendChild(sv("line", { x1:X(t), x2:X(t), y1:30, y2:190,
        stroke:"#222a34", "stroke-width":.5 }));
      const tx = sv("text", { x:X(t), y:207, fill:"#67788c",
        "font-size":"11", "text-anchor":"middle" });
      tx.textContent = t + "등급"; svg.appendChild(tx);
    }
    for (const d of [0, .4, .8, 1.2]) {
      svg.appendChild(sv("line", { x1:64, x2:576, y1:Y(d), y2:Y(d),
        stroke:"#222a34", "stroke-width":.5 }));
      const tx = sv("text", { x:56, y:Y(d)+4, fill:"#67788c",
        "font-size":"10", "text-anchor":"end",
        "font-family":"ui-monospace,monospace" });
      tx.textContent = d.toFixed(1); svg.appendChild(tx);
    }
    for (const q of Q_NAME) {
      const ds = D.theory.dissonance[q];
      let path = "";
      ds.forEach((d, t) => { path += (t ? "L" : "M") + X(t) + " " + Y(d); });
      svg.appendChild(sv("path", { d: path, fill:"none",
        stroke: COLOR[q], "stroke-width":1.6 }));
      ds.forEach((d, t) => {
        const c = sv("circle", { cx:X(t), cy:Y(d), r:4, fill:COLOR[q],
          style:"cursor:pointer" });
        c.addEventListener("click", () =>
          playChord(at(B.meaning[t + "/" + q],
                       clampRoot(B.meaning[t + "/" + q], 55)), .9));
        const ti = document.createElementNS(NS, "title");
        ti.textContent = `${t}등급 ${Q_KO[q]} (${B.meaning[t + "/" + q].join(",")}) — 거칢 ${d}`;
        c.appendChild(ti); svg.appendChild(c);
      });
    }
    const cap = sv("text", { x:70, y:18, fill:"#9fb0c4", "font-size":"11.5" });
    cap.textContent = "의미 화음의 불협화도 — 성질마다 6개의 고른 계단 (점을 누르면 들린다)";
    svg.appendChild(cap);
    box.appendChild(svg);

    // 사분면 격자
    const grid = el("div", { class: "quad" });
    const quads = [["흔함×장","major",0],["흔함×단","minor",0],
                   ["드묾×장","major",5],["드묾×단","minor",5]];
    for (const [label, q, t] of quads) {
      const cell = el("div", { class: "quadcell" });
      cell.style.borderColor = COLOR[q];
      const v = B.meaning[t + "/" + q];
      const h = el("div", { class: "quadhead" });
      h.appendChild(el("b", null, label));
      h.appendChild(el("span", { class: "mono dim" },
        " (" + v.join(",") + ")"));
      cell.appendChild(h);
      const words = (D.theory.quadrants.ko[label] || []).slice(0, 4)
        .map(w => w[0]).join(" · ");
      const wordsEn = (D.theory.quadrants.en[label] || []).slice(0, 3)
        .map(w => w[0]).join(" · ");
      cell.appendChild(el("div", { class: "dim", style:"font-size:.85rem" },
        words));
      cell.appendChild(el("div", { class: "dim mono",
        style:"font-size:.72rem" }, wordsEn));
      const b = el("button", { class: "chip", type: "button" }, "♪ 듣기");
      b.addEventListener("click", () => playChord(at(v, clampRoot(v, 55)), 1.1));
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
      const b = el("button", { class: "chip", type: "button" }, "♪ 글리프");
      b.addEventListener("click", () => {
        // 주어 자리에 놓았을 때의 글리프를 차례로 들려준다
        const qi = { major:0, minor:1, neutral:2 }[qual];
        const ev = W.encodeGlyph(3, isC ? 0 : 1, isC ? null : lang,
                                 +tier, qi, isC ? ci : +idx, 1, 0, +pol);
        let t = 0;
        for (const e of ev) {
          setTimeout(((ps, d) => () => playChord(ps, Math.max(.25, d * .09)))
                     (e.p, e.d), t);
          t += Math.max(250, e.d * 90);
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
    let i = 0, state = "role", quality = null, roleIdx = null;
    while (i < chords.length) {
      const k = R.key(chords[i]);
      if (state === "role") {
        if (T.TERM[k] !== undefined) { i++; continue; }
        if (T.ROLE[k] === undefined) return { state: "오류",
          hint: `${i + 1}번째 화음이 역할 화음이 아니다` };
        roleIdx = T.ROLE[k]; state = "head"; i++; continue;
      }
      if (state === "head") {
        if (T.LANG[k] !== undefined) { i++; continue; }   // 다음은 의미
        if (T.LETTER[k] !== undefined) { quality = "neutral"; state = "digit"; i++; continue; }
        const cell = T.MEANING[k];
        if (cell === undefined) return { state: "오류",
          hint: `${i + 1}번째 화음이 머리 화음이 아니다` };
        quality = cell.split("/")[1]; state = "digit"; i++; continue;
      }
      if (state === "digit") {
        if (T.CLOSE[k] !== undefined) { state = "role"; i++; continue; }
        if (T.DIGIT[quality][k] === undefined) return { state: "오류",
          hint: `${i + 1}번째 화음이 ${Q_KO[quality]} 자릿 화음도 맺음 화음도 아니다` };
        i++; continue;
      }
    }
    return { state, quality, roleIdx };
  }

  function candidates(exp) {
    // 지금 상태에서 눌러 넣을 수 있는 화음들.
    const out = [];
    if (exp.state === "오류") return out;
    if (exp.state === "role") {
      K.roles.forEach((r, i) => out.push({
        label: r, cls: "marker",
        p: at(B.role[i], K.rolePitch[i]) }));
      K.terminators.forEach((t, i) => out.push({
        label: "종결 " + t, cls: "marker",
        p: at(B.term[i], clampRoot(B.term[i], 48)) }));
    } else if (exp.state === "head") {
      for (let t = 0; t < 6; t++) for (const q of Q_NAME)
        out.push({ label: `${t}·${Q_KO[q]}`, cls: q,
          p: at(B.meaning[t + "/" + q], clampRoot(B.meaning[t + "/" + q], 48)) });
      for (const lg of ["ko", "en"]) {
        out.push({ label: lg + " 전용", cls: "marker",
          p: at(B.language[lg], clampRoot(B.language[lg], 48)) });
        out.push({ label: lg + " 글자", cls: "marker",
          p: at(B.letter[lg], clampRoot(B.letter[lg], 48)) });
      }
    } else if (exp.state === "digit") {
      const band = K.band[exp.roleIdx ?? 3];
      const shapes = B.digit[exp.quality];
      for (let d = 0; d < 32; d++) {
        const offI = Math.floor(d / shapes.length), shI = d % shapes.length;
        out.push({ label: String(d), cls: exp.quality,
          p: at(shapes[shI], band + K.digitOffsets[offI]) });
      }
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
    const stName = { role: "역할 화음 (또는 종결)", head: "머리 화음",
                     digit: "자릿 화음 (또는 맺음)", "오류": "오류" }[exp.state];
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
    "역할": "모양 → 문장 성분 · 근음 → 음역",
    "언어": "이 말에만 있는 낱말이 온다",
    "받아적기": "글자를 하나씩 적는다",
    "의미": "등급(빈도) × 성질(감정)",
    "자리": "32진법 자릿수 = 근음 어긋남 × 화음 모양",
    "맺음": "글리프의 끝 · 어절 경계",
    "종결": "문장의 끝",
  };
  let cine = { raf: null, srcNode: null };

  function digitsOf(index) {
    const out = []; let m = index + 1;
    while (m > 0) { const r = m % 32 || 32; out.push(r - 1); m = (m - r) / 32; }
    return out.reverse();
  }

  function openCinema(piece, text) {
    const host = $("#cinema");
    host.hidden = false;
    document.body.style.overflow = "hidden";
    const sched = W.schedule(piece.notes, 72);
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
    function drawAsm(n) {
      asm.textContent = "";
      // 25반음 세로 눈금
      for (let p = K.lowest; p <= K.highest; p++) {
        const y = 12 + (K.highest - p) * (AH - 26) / 24;
        asm.appendChild(sv("line", { x1: 320, x2: p % 12 === 0 ? 545 : 535,
          y1: y, y2: y, stroke: p % 12 === 0 ? "#2c3745" : "#1b232d",
          "stroke-width": p % 12 === 0 ? 1 : .5 }));
        if (p % 12 === 0) {
          const t = sv("text", { x: 552, y: y + 3, fill: "#5b6b7f",
            "font-size": "9", "font-family": "ui-monospace,monospace" });
          t.textContent = nm(p); asm.appendChild(t);
        }
      }
      if (!n) return;
      // 왼쪽: 규칙 서술 (글자만, 선으로 연결)
      const put = (x, y, txt, size, color) => {
        const t = sv("text", { x, y, fill: color || "#c8d4e2",
          "font-size": size || 12 });
        t.textContent = txt; asm.appendChild(t); return t;
      };
      put(6, 26, n.src, 15, "#e6edf5");
      put(6, 46, n.slot + " 화음", 11, "#e9b44c");
      put(6, 62, SLOT_RULE[n.slot] || "", 10, "#67788c");
      if (n.kind === 0 || n.kind === 1) {
        put(6, 92, (n.kind === 0 ? "개념" : "낱말") + " #" + n.idx, 11, "#9fb0c4");
        const ds = digitsOf(n.idx);
        put(6, 108, "32진법: [" + ds.join(" ") + "]", 10, "#67788c");
      }
      put(6, 138, n.role, 11, "#9fb0c4");
      put(6, 154, n.p.map(nm).join(" + "), 12, "#e6edf5");
      // 연결선과 현재 화음
      const q = (n.slot === "의미" || n.slot === "자리")
        && (n.kind === 0 || n.kind === 1) ? Q_NAME[n.qi] : null;
      const col = q ? COLOR[q] : "#8fa3b8";
      for (const p of n.p) {
        const y = 12 + (K.highest - p) * (AH - 26) / 24;
        asm.appendChild(sv("line", { x1: 205, x2: 320, y1: 150, y2: y,
          stroke: col, "stroke-width": .6, "stroke-opacity": .7 }));
        asm.appendChild(sv("rect", { x: 320, y: y - 2.5, width: 215,
          height: 5, fill: col, "fill-opacity": .85 }));
      }
    }
    drawAsm(null);

    // 재생 + 동기
    const pcm = W.synth(piece.notes, 72);
    const c = audio();
    const buf = c.createBuffer(1, pcm.length, W.SR);
    const chd = buf.getChannelData(0);
    for (let i = 0; i < pcm.length; i++) chd[i] = pcm[i] / 32768;
    const srcN = c.createBufferSource();
    srcN.buffer = buf; srcN.connect(c.destination);
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
      if (i !== cur && i >= 0) {
        cur = i;
        const n = sched[i][2];
        drawAsm(n);
        for (const r of rects)
          r.el.setAttribute("fill-opacity", r.i === i ? .95 : r.i < i ? .5 : .25);
        wordEls.forEach(w => w.el.classList.toggle("on",
          w.si === n.si && w.wi === n.w));
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

  window.SoriStudio = { renderTheory, searchFull, refreshPiano,
                        openCinema, closeCinema, playChord,
                        expectation, candidates };
})();
