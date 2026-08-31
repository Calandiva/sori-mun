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

  function koWord(c, roleName, grams) {
    const [ko, kt, , , , , conj] = c;
    const past = grams.includes("past");
    if (conj) {
      if (roleName === "서술어") return past ? conj[1] : conj[0];
      if (roleName === "관형어") return past ? conj[3] : conj[2];
      if (roleName === "부사어") return conj[4];
      return conj[0];
    }
    let w = ko;
    if (grams.includes("plural")) w += "들";
    if (roleName === "주어" || roleName === "보어") return part(w, "이", "가");
    if (roleName === "목적어") return part(w, "을", "를");
    if (roleName === "관형어") return kt === "MM" ? w : w + "의";
    if (roleName === "부사어") return (kt === "MAG" || kt === "MAJ") ? w : w + "에";
    if (roleName === "서술어") return part(w, "이", "") + (past ? "었다" : "다");
    return w;
  }

  function toKorean(items, term) {
    const cs = chunks(items);
    if (!cs.some(c => K.roles[c.role] === "서술어")) {
      const i = cs.findIndex(c => K.roles[c.role] === "보어" && c.it.c[6]);
      if (i >= 0) cs[i].role = R["서술어"];
    }
    const out = [];
    for (const roleName of ORDER_KO)
      for (const ch of cs) {
        if (K.roles[ch.role] !== roleName) continue;
        if (ch.it.c[1] === "∅") continue;
        for (const m of ch.mods) out.push(koWord(m.c, "관형어", []));
        out.push(koWord(ch.it.c, roleName, ch.grams));
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
  const addS = (w) => /(s|x|z|ch|sh)$/.test(w) ? w + "es"
    : /[^aeiou]y$/.test(w) ? w.slice(0, -1) + "ies" : w + "s";
  function inflect(w, g) {
    if (g === "past") return IRR[w] || (/e$/.test(w) ? w + "d"
      : /[^aeiou]y$/.test(w) ? w.slice(0, -1) + "ied" : w + "ed");
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
    const parts = [];
    for (const roleName of ORDER_EN)
      for (const ch of cs) {
        if (K.roles[ch.role] !== roleName) continue;
        let [, , en, et] = ch.it.c;
        if (!en || et === "∅") continue;
        const grams = ch.grams.concat([]);
        if (roleName === "서술어" && et === "VB" && third
            && !grams.some(g => ["past","third","ing","will"].includes(g)))
          grams.push("third");
        if (grams.includes("will")) parts.push("will");
        const copular = (roleName === "서술어" && (et === "JJ" || et === "NN"))
          || (roleName === "보어" && !hasVerb && (et === "JJ" || et === "NN"));
        if (copular) {
          parts.push(grams.includes("past") ? "was" : "is");
          if (grams.includes("not")) parts.push("not");
          parts.push(en); continue;
        }
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

  window.SoriRead = { read, decodeGlyph, toKorean, toEnglish, key, root };
})();
