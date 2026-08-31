/* 되읽기 — 브라우저에서 소리를 뜻으로.
 *
 * 파이썬의 sorimun.core.glyph.decode / sorimun.generate 를 그대로 옮긴
 * 것이다. 되읽기에는 형태소 분석기가 필요 없고 화음 은행과 개념표만
 * 있으면 되므로 브라우저에서도 똑같이 돌아간다.
 *
 * 보는 것은 화음의 차례뿐이다. 길이는 보지 않는다. */
(function () {
  "use strict";
  const D = window.SORIMUN;
  const K = D.codes, B = D.banks;

  const key = (ps) => { const s = [...ps].sort((a, b) => a - b);
    return s.map(p => p - s[0]).join(","); };
  const root = (ps) => Math.min(...ps);

  const ROLE = {}, MEANING = {}, LANG = {}, LETTER = {}, DIGIT = {},
        CLOSE = {}, TERM = {};
  B.role.forEach((v, i) => ROLE[v.join(",")] = i);
  Object.entries(B.meaning).forEach(([k, v]) => MEANING[v.join(",")] = k);
  Object.entries(B.language).forEach(([k, v]) => LANG[v.join(",")] = k);
  Object.entries(B.letter).forEach(([k, v]) => LETTER[v.join(",")] = k);
  Object.entries(B.digit).forEach(([q, list]) => {
    DIGIT[q] = {}; list.forEach((v, i) => DIGIT[q][v.join(",")] = i); });
  B.close.forEach((v, i) => CLOSE[v.join(",")] = i);
  B.term.forEach((v, i) => TERM[v.join(",")] = K.terminators[i]);

  function indexOf(digits) {
    let m = 0;
    for (const d of digits) m = m * K.base + (d + 1);
    return m - 1;
  }

  function decodeGlyph(chords, i) {
    const r = ROLE[key(chords[i])];
    if (r === undefined) throw new Error(`${i}번째 화음은 역할 화음이 아닙니다`);
    const off = root(chords[i]) - K.rolePitch[r];
    const flagIdx = K.flagOffsets.indexOf(off);
    if (flagIdx < 0) throw new Error(`${i}번째 역할 화음의 근음이 맞지 않습니다`);
    let j = i + 1;
    if (j >= chords.length) throw new Error("머리 화음이 없습니다");

    let kind = "개념", lang = null, tier = -1, quality = "neutral";
    let k = key(chords[j]);
    if (LANG[k] !== undefined) {
      kind = "낱말"; lang = LANG[k]; j++;
      if (j >= chords.length) throw new Error("의미 화음이 없습니다");
      k = key(chords[j]);
    } else if (LETTER[k] !== undefined) {
      kind = "글자"; lang = LETTER[k]; j++;
    }
    if (kind !== "글자") {
      const cell = MEANING[k];
      if (cell === undefined) throw new Error(`${j}번째 화음은 의미 화음이 아닙니다`);
      const [t, q] = cell.split("/");
      tier = +t; quality = q; j++;
    }

    const band = K.band[r], table = DIGIT[quality];
    const nshape = B.digit[quality].length;
    const digits = []; let close = null;
    while (j < chords.length) {
      const kv = key(chords[j]);
      if (CLOSE[kv] !== undefined) { close = CLOSE[kv]; j++; break; }
      const sh = table[kv];
      if (sh === undefined) throw new Error(`${j}번째 화음은 자릿 화음이 아닙니다`);
      const o = root(chords[j]) - band;
      const oi = K.digitOffsets.indexOf(o);
      if (oi < 0) throw new Error(`${j}번째 자릿 화음의 근음이 맞지 않습니다`);
      digits.push(oi * nshape + sh); j++;
    }
    if (close === null) throw new Error("맺음 화음이 없습니다");
    if (!digits.length) throw new Error("자릿 화음이 없습니다");
    return { role: r, kind, lang, tier, quality, close,
             flag: flagIdx, index: indexOf(digits), next: j };
  }

  function read(chords) {
    const items = []; const warn = [];
    let i = 0, group = 0, chars = [], charRole = 0, charLang = "ko", term = ".";
    const flush = () => { if (chars.length) {
      items.push({ kind: "글자", form: chars.join(""), role: charRole,
                   lang: charLang, group }); chars = []; } };
    while (i < chords.length) {
      const t = TERM[key(chords[i])];
      if (t !== undefined) { flush(); term = t; i++; continue; }
      let g;
      try { g = decodeGlyph(chords, i); }
      catch (e) { warn.push(e.message); break; }
      i = g.next;
      if (g.kind === "글자") {
        let ch = D.alphabet[g.lang][g.index] || "?";
        if (g.flag && !chars.length) ch = ch.toUpperCase();
        chars.push(ch); charRole = g.role; charLang = g.lang;
        if (g.close === 1) flush();
      } else {
        flush();
        if (g.kind === "개념") {
          const c = D.concepts[g.index];
          if (!c) { warn.push(`개념 ${g.index} 이 표에 없습니다`); }
          else items.push({ kind: "개념", c, idx: g.index, role: g.role,
                            group, flag: g.flag });
        } else {
          items.push({ kind: "낱말", role: g.role, lang: g.lang,
                       tier: g.tier, quality: g.quality, index: g.index,
                       group, flag: g.flag });
        }
      }
      if (g.close === 1) group++;
    }
    flush();
    return { items, terminator: term, warnings: warn };
  }

  function readAll(chords) {
    // 종결 화음으로 문장을 가른다 — 은행이 서로소라 안전하다
    const parts = [];
    let cur = [];
    for (const c of chords) {
      cur.push(c);
      if (TERM[key(c)] !== undefined) { parts.push(cur); cur = []; }
    }
    if (cur.length) parts.push(cur);
    return parts.map(read);
  }

  /* 다른 말로 지을 때: 정확한 개념은 그대로, 전용 낱말은 근사 개념으로,
     받아 적힌 낱말은 글자 그대로 (고유명사는 옮기지 않는 것이 맞다). */
  function crossItems(items) {
    const W = window.SoriWrite;
    const out = [];
    for (const it of items) {
      if (it.kind === "개념") { out.push(it); continue; }
      if (it.kind === "글자") {
        out.push({ kind: "개념", role: it.role, group: it.group,
                   c: [it.form, "RAW", it.form, "RAW", 0, 0] });
        continue;
      }
      if (!W) continue;
      const found = W.lookupRev(it.lang, it.tier, it.quality, it.index);
      if (!found) continue;
      const ci = W.approxOf(it.lang, found[0], found[1]);
      if (ci != null)
        out.push({ kind: "개념", role: it.role, group: it.group,
                   c: D.concepts[ci], idx: ci, approx: true });
    }
    return out;
  }

  /* 적은 말 그대로 되짓는다 — 브라우저 인코더의 역. */
  function toSame(items, term, lang) {
    const W = window.SoriWrite;
    const groups = [];
    for (const it of items) {
      if (!groups.length || groups[groups.length-1][0].group !== it.group)
        groups.push([it]);
      else groups[groups.length-1].push(it);
    }
    const words = [];
    for (const g of groups) {
      if (lang === "ko") {
        let out = "", morphs = [];
        const flush = () => {
          if (!morphs.length) return;
          const j = W ? W.joinKo(morphs) : null;
          out += j != null ? j : morphs.map(m => m[0]).join("");
          morphs = [];
        };
        for (const it of g) {
          if (it.kind === "글자") { flush(); out += it.form; }
          else if (it.kind === "개념") {
            const c = it.c;
            if (c[1] === "∅") continue;
            morphs.push([c[0], c[1]]);
          } else if (W) {
            const f = W.lookupRev(it.lang, it.tier, it.quality, it.index);
            if (f) morphs.push(f); else morphs.push(["?", "?"]);
          }
        }
        flush();
        if (out) words.push(out);
      } else {
        let out = "";
        for (const it of g) {
          if (it.kind === "글자") out += it.form;
          else if (it.kind === "개념") {
            const c = it.c;
            if (c[3] === "GRAM") { out = out ? inflect(out, GRAM[c[2]]) : out; continue; }
            if (c[3] === "∅" || !c[2]) continue;
            let f = c[2];
            if (it.flag) f = f[0].toUpperCase() + f.slice(1);
            out += f;
          } else if (W) {
            const found = W.lookupRev(it.lang, it.tier, it.quality, it.index);
            let f = found ? found[0] : "?";
            if (it.flag) f = f[0].toUpperCase() + f.slice(1);
            out += f;
          }
        }
        if (out) words.push(out);
      }
    }
    return words.length ? words.join(" ") + term : "";
  }

  /* ── 생성 ── */
  const GRAM = { "«past»": "past", "«will»": "will", "«plural»": "plural",
                 "«not»": "not", "«3sg»": "third", "«ing»": "ing" };
  const R = {};  // 자리 이름 → 번호
  K.roles.forEach((n, i) => R[n] = i);

  function chunks(items) {
    const out = []; let pending = [], orphan = [];
    for (const it of items) {
      if (it.kind !== "개념") continue;
      const [, , en, et] = it.c;
      if (et === "GRAM") {
        const g = GRAM[en];
        if (out.length && out[out.length - 1].group === it.group)
          out[out.length - 1].grams.push(g);
        else orphan.push(g);
        continue;
      }
      if (K.roles[it.role] === "관형어") { pending.push(it); continue; }
      out.push({ it, role: it.role, grams: orphan.concat([]),
                 mods: pending, group: it.group });
      pending = []; orphan = [];
    }
    if (pending.length && out.length) out[out.length - 1].mods.push(...pending);
    return out;
  }

  const hasFinal = (w) => { if (!w) return false;
    const c = w.charCodeAt(w.length - 1);
    if (c < 0xac00 || c > 0xd7a3) return true;
    return (c - 0xac00) % 28 !== 0; };
  const part = (w, a, b) => w + (hasFinal(w) ? a : b);

  const ORDER_KO = ["독립어", "관형어", "주어", "보어", "부사어", "목적어", "서술어"];
  const ORDER_EN = ["독립어", "관형어", "주어", "서술어", "목적어", "보어", "부사어"];

  const IRR_SUBJ = { "나": "내가", "너": "네가", "저": "제가", "누구": "누가" };
  function koWord(c, roleName, grams, linking) {
    const [ko, kt, , , , , conj] = c;
    if (kt === "RAW") {
      if (roleName === "주어") return ko + (hasFinal(ko) ? "이" : "가");
      if (roleName === "목적어") return ko + (hasFinal(ko) ? "을" : "를");
      if (roleName === "관형어") return ko + "의";
      return ko;
    }
    const past = grams.includes("past");
    if (conj) {
      if (roleName === "서술어" && linking){
        // "길고 힘들다" 의 앞쪽 — 관형형 대신 고 연결로 어림한다
        const stem = conj[2].replace(/[ᄂ-ᇿㄴ은는]$/,"");
        return (stem||ko) + "고";
      }
      if (roleName === "서술어") return past ? conj[1] : conj[0];
      if (roleName === "관형어") return past ? conj[3] : conj[2];
      if (roleName === "부사어") return conj[4];
      return conj[0];
    }
    let w = ko;
    if (grams.includes("plural")) w += "들";
    if (roleName === "주어" && IRR_SUBJ[w]) return IRR_SUBJ[w];
    if (roleName === "주어" || roleName === "보어") return part(w, "이", "가");
    if (roleName === "목적어") return part(w, "을", "를");
    if (roleName === "관형어") return kt === "MM" ? w : w + "의";
    if (roleName === "부사어") return (kt === "MAG" || kt === "MAJ") ? w : w + "에";
    if (roleName === "서술어") {
      if (kt === "NNG" || kt === "NNP" || kt === "XR")
        return w + (past ? "했다" : "한다");    // 사랑한다
      return part(w, "이", "") + (past ? "었다" : "다");
    }
    return w;
  }

  function toKorean(items, term) {
    const cs = chunks(items);
    if (!cs.some(c => K.roles[c.role] === "서술어"))
      for (const c of cs)
        if (K.roles[c.role] === "보어" && c.it.c[6]) c.role = R["서술어"];
    const preds = cs.filter(c => K.roles[c.role] === "서술어");
    const out = [];
    for (const roleName of ORDER_KO)
      for (const ch of cs) {
        if (K.roles[ch.role] !== roleName) continue;
        if (ch.it.c[1] === "∅") continue;
        for (const m of ch.mods) out.push(koWord(m.c, "관형어", []));
        const linking = roleName === "서술어" && preds.length > 1
          && ch !== preds[preds.length - 1];
        out.push(koWord(ch.it.c, roleName, ch.grams, linking));
      }
    return out.length ? out.join(" ") + term : "";
  }

  const NO_ART = new Set(["love","death","life","time","peace","war","hope",
    "fear","sadness","joy","beauty","music","money","work","blood","air"]);
  const IRR = {be:"was",become:"became",come:"came",go:"went",see:"saw",
    hear:"heard",know:"knew",make:"made",take:"took",give:"gave",find:"found",
    feel:"felt",hold:"held",sing:"sang",run:"ran",sit:"sat",stand:"stood",
    write:"wrote",read:"read",eat:"ate",drink:"drank",sleep:"slept",
    fall:"fell",fly:"flew",shake:"shook",shine:"shone",say:"said",
    think:"thought",begin:"began",break:"broke",bring:"brought",buy:"bought",
    catch:"caught",teach:"taught",tell:"told",win:"won",lose:"lost"};
  const IRR_PL = {child:"children",man:"men",woman:"women",person:"people",
    foot:"feet",tooth:"teeth",mouse:"mice",goose:"geese",life:"lives",
    leaf:"leaves",knife:"knives",wife:"wives"};
  const addS = (w) => /(s|x|z|ch|sh)$/.test(w) ? w + "es"
    : /[^aeiou]y$/.test(w) ? w.slice(0, -1) + "ies" : w + "s";
  function inflect(w, g) {
    if (g === "past") return IRR[w] || (/e$/.test(w) ? w + "d"
      : /[^aeiou]y$/.test(w) ? w.slice(0, -1) + "ied" : w + "ed");
    if (g === "plural" && IRR_PL[w]) return IRR_PL[w];
    if (g === "third" || g === "plural") return addS(w);
    if (g === "ing") return /e$/.test(w) && !/ee$/.test(w)
      ? w.slice(0, -1) + "ing" : w + "ing";
    return w;
  }

  function toEnglish(items, term) {
    const cs = chunks(items);
    const hasVerb = cs.some(c => K.roles[c.role] === "서술어" && c.it.c[3] === "VB");
    const subj = cs.find(c => K.roles[c.role] === "주어");
    const third = subj && !["i","you","we","they"].includes(subj.it.c[2])
      && !subj.grams.includes("plural");
    const OBJ_PRP = { i:"me", he:"him", she:"her", we:"us", they:"them", who:"whom" };
    let copulaDone = false;
    const parts = [];
    for (const roleName of ORDER_EN)
      for (const ch of cs) {
        if (K.roles[ch.role] !== roleName) continue;
        let [, , en, et] = ch.it.c;
        if (!en || et === "∅") continue;
        if (et === "RAW") { parts.push(en); continue; }
        const grams = ch.grams.concat([]);
        if (roleName === "서술어" && et === "VB" && third
            && !grams.some(g => ["past","third","ing","will"].includes(g)))
          grams.push("third");
        if (grams.includes("will")) parts.push("will");
        const W2 = window.SoriWrite;
        if (roleName === "서술어" && et === "NN" && W2 && W2.inDict("en", en, "VB"))
          et = "VB";                                   // 사랑하다 → loves
        if (roleName === "서술어" && et === "VB" && third
            && !grams.some(g => ["past","third","ing","will"].includes(g)))
          grams.push("third");
        const copular = (roleName === "서술어" && (et === "JJ" || et === "NN"))
          || (roleName === "보어" && !hasVerb && (et === "JJ" || et === "NN"));
        if (copular) {
          if (copulaDone) parts.push("and");
          else { parts.push(grams.includes("past") ? "was" : "is"); copulaDone = true; }
          if (grams.includes("not")) parts.push("not");
          parts.push(en); continue;
        }
        if (roleName === "목적어" && et === "PRP" && OBJ_PRP[en]) en = OBJ_PRP[en];
        if (["주어","목적어","보어"].includes(roleName) && et === "NN"
            && !grams.includes("plural") && !NO_ART.has(en)) parts.push("the");
        for (const m of ch.mods) if (m.c[2] && m.c[3] !== "∅") parts.push(m.c[2]);
        for (const g of grams)
          if (["past","plural","third","ing"].includes(g)) en = inflect(en, g);
        parts.push(en);
      }
    if (!parts.length) return "";
    const s = parts.join(" ");
    return s[0].toUpperCase() + s.slice(1) + term;
  }

  /* ── 소리에서 화음 읽기 — 파이썬 wave_read 와 같은 잣대 ──
     화음 사이 무음으로 가르고, 구간마다 25개 후보 음의 힘을 골츠엘로
     재고, 이미 고른 음의 배음으로 설명되는 것은 거른다. */
  const PARTIAL_GAIN = { 2: .28, 3: .14, 4: .06 };
  const AR = { silence: .045, minSeg: .12, floor: .20, margin: 2.2 };
  const fq = m => 440 * Math.pow(2, (m - 69) / 12);

  function goertzel(x, a, b, sr, freq) {
    const n = b - a;
    const k = 2 * Math.cos(2 * Math.PI * freq / sr);
    let s0 = 0, s1 = 0;
    for (let i = 0; i < n; i++) {
      const w = .5 - .5 * Math.cos(2 * Math.PI * i / n);
      const t = x[a + i] * w + k * s0 - s1;
      s1 = s0; s0 = t;
    }
    return (s1 * s1 + s0 * s0 - k * s0 * s1) / n;
  }

  function chordsFromSamples(x, sr) {
    const win = Math.max(1, Math.floor(sr / 200));
    const nw = Math.floor(x.length / win);
    const rms = new Float64Array(nw);
    let peak = 0;
    for (let i = 0; i < nw; i++) {
      let s = 0;
      for (let j = i * win; j < (i + 1) * win; j++) s += x[j] * x[j];
      rms[i] = Math.sqrt(s / win);
      peak = Math.max(peak, rms[i]);
    }
    if (peak <= 0) return [];
    const thr = peak * AR.silence;
    const segs = [];
    let start = null;
    for (let i = 0; i < nw; i++) {
      if (rms[i] >= thr && start === null) start = i;
      else if (rms[i] < thr && start !== null) {
        segs.push([start * win, i * win]); start = null;
      }
    }
    if (start !== null) segs.push([start * win, nw * win]);

    const out = [];
    for (const [a0, b0] of segs) {
      if ((b0 - a0) / sr < AR.minSeg) continue;
      const n = b0 - a0;
      let a = a0 + Math.floor(n * .15), b = a0 + Math.floor(n * .85);
      if (b - a < 256) { a = a0; b = b0; }
      const power = {};
      let strongest = 0;
      for (let m = K.lowest; m <= K.highest; m++) {
        power[m] = goertzel(x, a, b, sr, fq(m));
        strongest = Math.max(strongest, power[m]);
      }
      if (strongest <= 0) continue;
      const chosen = [];
      for (let m = K.lowest; m <= K.highest; m++) {
        const p = power[m];
        if (p < strongest * AR.floor) continue;
        let expected = 0;
        for (const c of chosen) {
          const d = fq(m) / fq(c), k = Math.round(d);
          if (PARTIAL_GAIN[k] && Math.abs(d - k) < .03)
            expected += power[c] * PARTIAL_GAIN[k] * PARTIAL_GAIN[k];
        }
        if (expected > 0 && p < expected * AR.margin) continue;
        chosen.push(m);
        if (chosen.length === 3) break;
      }
      if (chosen.length) out.push(chosen);
    }
    return out;
  }

  window.SoriRead = { read, readAll, decodeGlyph, toKorean, toEnglish,
                      toSame, crossItems, chordsFromSamples, key, root };
})();
