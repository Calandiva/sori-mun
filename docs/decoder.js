/* 되읽기 — 브라우저에서 소리를 뜻으로.
 *
 * 파이썬의 sorimun.core.glyph.decode / sorimun.generate 를 그대로 옮긴
 * 것이다. 되읽기에는 형태소 분석기가 필요 없고 개념표만 있으면 되므로
 * 브라우저에서도 똑같이 돌아간다.
 *
 * 보는 것은 화음의 차례뿐이다. 길이는 보지 않는다.
 * 모든 소리의 꼭대기가 멜로디다 — 베이스 C3 이 울리면 낱말의 머리,
 * 마지막 두 멜로디 음이 종지, 멜로디 없는 저음 이중음이 문장의 끝. */
(function () {
  "use strict";
  const D = window.SORIMUN;
  const K = D.codes;

  const srt = (ps) => [...ps].sort((a, b) => a - b);

  const ROLE_BY_INNER = {}, TERM = {}, KIND_BY_MARK = {};
  K.roleInner.forEach((v, i) => ROLE_BY_INNER[v] = i);
  Object.entries(K.termSet).forEach(([m, ps]) => TERM[srt(ps).join(",")] = m);
  Object.entries(K.kindMark).forEach(([kl, v]) => KIND_BY_MARK[v] = kl);
  const QUAL_BY_SIG = {}, TIER_BY_LEAP = {}, DEGREE = {};
  Object.entries(K.qualitySig).forEach(([q, v]) => QUAL_BY_SIG[v] = q);
  K.tierLeap.forEach((v, t) => TIER_BY_LEAP[v] = t);
  Object.entries(K.scale).forEach(([q, sc]) => {
    DEGREE[q] = {};
    K.digitOrder[q].forEach((deg, d) => DEGREE[q][sc[deg]] = d);
  });
  const TONIC_SET = new Set(K.tonics);

  const readTerm = (ps) =>
    (ps.length >= 2 && Math.max(...ps) <= 56)
      ? TERM[srt(ps).join(",")] : undefined;
  const isStart = (ps) =>
    ps.length >= 2 && Math.min(...ps) === K.pedal
      && TONIC_SET.has(Math.max(...ps));
  const tonicOf = (tier, qi, index) => {
    const n = K.tonics.length;
    return K.tonics[(index + 3 * Math.max(0, tier) + 5 * qi) % n];
  };

  function indexOf(digits, base) {
    let m = 0;
    for (const d of digits) m = m * base + (d + 1);
    return m - 1;
  }

  function decodeGlyph(chords, i) {
    const head = srt(chords[i]);
    if (!isStart(head))
      throw new Error(`${i}번째 소리는 낱말의 머리(베이스 C3 + 으뜸음)가 아닙니다`);
    const tonic = head[head.length - 1];
    if (head.length !== 3)
      throw new Error(`${i}번째 머리의 내성이 맞지 않습니다`);
    const r = ROLE_BY_INNER[head[1] - K.pedal];
    if (r === undefined)
      throw new Error(`${i}번째 머리의 역할 내성이 맞지 않습니다`);

    // 몸통 — 다음 머리나 종결까지. 꼭대기가 멜로디다.
    let j = i + 1;
    const body = [];
    while (j < chords.length) {
      const c = srt(chords[j]);
      if (isStart(c) || readTerm(c) !== undefined) break;
      body.push(c); j++;
    }
    if (body.length < 3)
      throw new Error("멜로디가 짧습니다 — 자릿음 하나와 종지 둘은 있어야 합니다");
    for (let k2 = 0; k2 < body.length; k2++)
      if (body[k2].length > 1 && k2 !== body.length - 2)
        throw new Error("표지 내성은 종지1 에만 설 수 있습니다");

    const sig1ev = body[body.length - 2];
    const sig1 = sig1ev[sig1ev.length - 1];
    let quality = QUAL_BY_SIG[sig1 - tonic];
    if (quality === undefined) throw new Error("종지1 이 으뜸음 위 3도류가 아닙니다");
    let tier = TIER_BY_LEAP[sig1 - body[body.length - 1][0]];
    if (tier === undefined) throw new Error("종지 하행이 등급이 아닙니다");

    let kind = 0, lang = null, flag = 0, join = false;
    for (const m of sig1ev.slice(0, -1)) {
      const kl = KIND_BY_MARK[m];
      if (kl !== undefined) {
        const [kn, lg] = kl.split("|");
        kind = kn === "WORD" ? 1 : 2; lang = lg;
      } else if (m === K.flagMark) flag = 1;
      else if (m === K.joinMark) join = true;
      else throw new Error(`모르는 표지 내성 ${m}`);
    }
    let qi = { major: 0, minor: 1, neutral: 2 }[quality];
    if (kind === 2) { tier = 0; quality = "neutral"; qi = 2; }

    const table = DEGREE[quality], base = K.scale[quality].length;
    const digits = [];
    for (let k2 = 0; k2 < body.length - 2; k2++) {
      const d = table[body[k2][0] - tonic];
      if (d === undefined)
        throw new Error(`홑음 ${body[k2][0]} 이 이 조의 ${quality} 음계에 없습니다`);
      digits.push(d);
    }
    const index = indexOf(digits, base);
    if (tonicOf(tier, qi, index) !== tonic)
      throw new Error("으뜸음이 낱말의 정체와 맞지 않습니다");
    return { role: r, kind: ["개념", "낱말", "글자"][kind], lang, tier,
             quality, flag, join, index, next: j };
  }

  function read(chords) {
    const items = []; const warn = [];
    let i = 0, group = 0, chars = [], charRole = 0, charLang = "ko", term = ".";
    const flush = () => { if (chars.length) {
      items.push({ kind: "글자", form: chars.join(""), role: charRole,
                   lang: charLang, group }); chars = []; } };
    while (i < chords.length) {
      const t = readTerm(chords[i]);
      if (t !== undefined) { flush(); term = t; i++; continue; }
      let g;
      try { g = decodeGlyph(chords, i); }
      catch (e) { warn.push(e.message); break; }
      i = g.next;
      const joined = g.join;
      if (g.kind === "글자") {
        let ch = D.alphabet[g.lang][g.index] || "?";
        if (g.flag && !chars.length) ch = ch.toUpperCase();
        chars.push(ch); charRole = g.role; charLang = g.lang;
        if (!joined) flush();
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
      if (!joined) group++;
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
      if (readTerm(c) !== undefined) {
        parts.push(cur); cur = [];
      }
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
  const AR = { silence: .045, minSeg: .12, minGap: .08, floor: .20, margin: 2.2 };
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

    // 간섭 딥 병합 — 진짜 경계 골(0.13s+)만 살아남는다
    const merged = [];
    for (const [a, b] of segs) {
      if (merged.length && (a - merged[merged.length - 1][1]) / sr < AR.minGap)
        merged[merged.length - 1][1] = b;
      else merged.push([a, b]);
    }

    const out = [];
    for (const [a0, b0] of merged) {
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
        if (chosen.length === 4) break;   // 종지1 + 표지 셋이 최대
      }
      if (chosen.length) out.push(chosen);
    }
    return out;
  }

  /* 부분집합에 없는 낱말이 든 문장인가 — 있으면 그 말의 전체 사전을
     내려받아 feedFull 로 채운 뒤 다시 읽으면 된다. */
  function unresolvedLangs(readings) {
    const W = window.SoriWrite, langs = new Set();
    if (!W) return [];
    for (const r of readings)
      for (const it of r.items)
        if (it.kind === "낱말"
            && !W.lookupRev(it.lang, it.tier, it.quality, it.index))
          langs.add(it.lang);
    return [...langs];
  }

  window.SoriRead = { read, readAll, decodeGlyph, toKorean, toEnglish,
                      toSame, crossItems, chordsFromSamples,
                      readTerm, isStart, tonicOf, unresolvedLangs,
                      tables: { ROLE_BY_INNER, KIND_BY_MARK, TERM,
                                QUAL_BY_SIG, TIER_BY_LEAP, DEGREE } };
})();
