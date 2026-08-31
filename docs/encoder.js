/* 적기 — 브라우저에서 글을 소리로.
 *
 * 파이썬 파이프라인(분석 → 자리 매기기 → 글리프)을 옮긴 것이다.
 * 다만 형태소 분석기는 실을 수 없으므로 한국어는 사전 앞머리 맞추기와
 * 활용표로 가른다. 갈리지 않는 어절은 글자로 받아 적는다 — 소리는
 * 길어지지만 정확성은 잃지 않는다.
 *
 * 스스로 지키는 약속: 여기서 적은 소리는 여기서 되읽으면 원문이
 * 글자까지 그대로 돌아온다. 어절마다 적기 전에 되지어 보고, 어긋나면
 * 받아 적는 쪽을 고른다. */
(function () {
  "use strict";
  const D = window.SORIMUN;
  const K = D.codes, B = D.banks, DUR = D.durations;
  const ET = D.enTagger, KT = D.koTags;
  const R_IDX = {}; K.roles.forEach((n, i) => R_IDX[n] = i);
  const Q_NAME = ["major", "minor", "neutral"];

  /* ── 사전 되찾기표 ── */
  // (꼴|품사) → [등급, 성질, 번호, 극성]
  const KO = new Map(), EN = new Map();
  // 성질/등급/번호 → 꼴|품사  (되읽기 표시용)
  const KO_REV = new Map(), EN_REV = new Map();
  for (const [f, t, tier, q, idx, pol] of D.dict.ko) {
    if (!KO.has(f + "|" + t)) KO.set(f + "|" + t, [tier, q, idx, pol]);
    KO_REV.set(tier + "/" + Q_NAME[q] + "/" + idx, f + "|" + t);
  }
  for (const [f, t, tier, q, idx, pol] of D.dict.en) {
    if (!EN.has(f + "|" + t)) EN.set(f + "|" + t, [tier, q, idx, pol]);
    EN_REV.set(tier + "/" + Q_NAME[q] + "/" + idx, f + "|" + t);
  }
  // 꼴 → 그 꼴을 가진 (품사, 자료) 목록
  const KO_FORMS = new Map(), EN_TAGS = new Map();
  for (const [f, t, tier, q, idx, pol] of D.dict.ko) {
    if (!KO_FORMS.has(f)) KO_FORMS.set(f, []);
    KO_FORMS.get(f).push([t, tier, q, idx, pol]);
  }
  for (const [f, t] of D.dict.en) {
    if (!EN_TAGS.has(f)) EN_TAGS.set(f, new Set());
    EN_TAGS.get(f).add(t);
  }
  // 개념: (말, 꼴, 품사) → 개념 번호   /  근사도 함께
  const CONCEPT_KO = new Map(), CONCEPT_EN = new Map();
  D.concepts.forEach((c, i) => {
    if (c[1] !== "∅") CONCEPT_KO.set(c[0] + "|" + c[1], i);
    CONCEPT_EN.set(c[2] + "|" + c[3], i);
  });
  const APPROX = new Map();
  for (const [lang, f, t, ci] of D.approx) APPROX.set(lang + "|" + f + "|" + t, ci);

  // 활용표: 표면형 → 형태소열 후보 / 형태소열 → 표면형(최저 비용)
  const INFLECT = new Map(), INV_INFLECT = new Map();
  for (const [surface, mstr, cost] of D.inflect) {
    if (!INFLECT.has(surface)) INFLECT.set(surface, []);
    INFLECT.get(surface).push([mstr, cost]);
    const cur = INV_INFLECT.get(mstr);
    if (!cur || cost < cur[1]) INV_INFLECT.set(mstr, [surface, cost]);
  }

  const GRAMMATICAL_KO = new Set(KT.grammatical);
  const SUBST_KO = new Set(KT.substantive);
  const PRED_KO = new Set(KT.predicate);
  const HANGUL = /^[가-힣]+$/;
  const SYL = /^[가-힣]/;

  /* ══ 글리프 적기 (glyph.py encode 의 포팅) ══ */
  function digitsOf(index, base) {
    const out = []; let m = index + 1;
    while (m > 0) { const r = m % base || base; out.push(r - 1);
      m = (m - r) / base; }
    return out.reverse();
  }
  function scaled(d, roleIdx) {
    const [num, den] = DUR.scale[K.roles[roleIdx]];
    return Math.max(1, Math.floor(d * num / den));
  }
  function chordAt(voicing, root) {
    return voicing.map(v => root + v);
  }
  function clampRoot(voicing, root) {
    const span = voicing[voicing.length - 1];
    return Math.min(root, K.highest - span);
  }

  // kind: 0=개념 1=낱말 2=글자
  function encodeGlyph(roleIdx, kind, lang, tier, qi, index, close, flag, pol) {
    const accent = DUR.vel.accent * Math.abs(pol || 0);
    let q = Q_NAME[qi], t = tier;
    if (kind === 2) { q = "neutral"; t = 0; }   // 글자의 고정 서명
    const ev = [];
    const put = (voicing, root, d, v, slot, rest) =>
      ev.push({ p: chordAt(voicing, root), d: scaled(d, roleIdx),
                v: Math.min(127, v), slot, rest: rest || 0 });
    const single = (p, d, v, slot) =>
      ev.push({ p: [p], d: scaled(d, roleIdx), v: Math.min(127, v),
                slot, rest: 0 });

    put(B.role[roleIdx], K.rolePitch[roleIdx] + K.flagOffsets[flag ? 1 : 0],
        DUR.role, DUR.vel.role + accent, "역할");
    if (kind === 1)
      put(B.language[lang], clampRoot(B.language[lang], 48),
          DUR.head, DUR.vel.head, "언어");
    if (kind === 2)
      put(B.letter[lang], clampRoot(B.letter[lang], 48),
          DUR.head, DUR.vel.head, "받아적기");

    const sig1 = K.melBase + K.qualitySig[q];
    single(sig1, DUR.sig, DUR.vel.sig + accent, "서명");
    single(sig1 + K.tierLeap[t], DUR.sig, DUR.vel.sig + accent, "서명");
    const scale = K.scale[q], base = scale.length;
    for (const d of digitsOf(index, base))
      single(K.melBase + scale[d], DUR.digit, DUR.vel.digit + accent, "이름");

    put(B.close[close], clampRoot(B.close[close], 48),
        DUR.close, DUR.vel.close, "맺음",
        close === 1 ? 3 : 1);
    return ev;
  }
  function terminatorEvent(mark) {
    const i = Math.max(0, K.terminators.indexOf(mark));
    return { p: chordAt(B.term[i], clampRoot(B.term[i], 48)),
             d: DUR.term, v: DUR.vel.term, slot: "종결", rest: 8 };
  }

  /* ══ 한국어 — 사전 앞머리 맞추기 ══ */
  function rarity(lang, form, tag) {
    const e = (lang === "ko" ? KO : EN).get(form + "|" + tag);
    return e ? e[0] * 1e7 + e[2] : 1e9;
  }
  function parseMarkers(rest) {
    // 남은 글자를 표지들로 가른다. 긴 것부터, 물러서기 포함.
    if (!rest) return [];
    for (let cut = rest.length; cut >= 1; cut--) {
      const piece = rest.slice(0, cut);
      if (!SYL.test(piece)) continue;
      const cands = KO_FORMS.get(piece);
      if (!cands) continue;
      for (const [t] of cands) {
        if (!GRAMMATICAL_KO.has(t)) continue;
        const tail = parseMarkers(rest.slice(cut));
        if (tail !== null) return [[piece, t], ...tail];
      }
    }
    return null;
  }
  function chainOk(morphs) {
    // 형태소가 문법에 맞게 이어지는가. VV 뒤에 바로 조사가 오는 따위의
    // 파스를 거른다 (물이 = 묻/VV + 이/JKS 는 말이 안 된다).
    let prev = null;
    for (const [, t] of morphs) {
      if (prev !== null) {
        if (t.startsWith("J")) {
          const ok = SUBST_KO.has(prev) || ["ETN", "XSN", "NNB"].includes(prev)
            || prev.startsWith("J");
          if (!ok) return false;
        } else if (["EP", "EF", "EC", "ETM", "ETN"].includes(t)) {
          const ok = PRED_KO.has(prev) || ["XSV", "XSA", "EP"].includes(prev);
          if (!ok) return false;
        }
      }
      prev = t;
    }
    return true;
  }

  function parseEojeol(core) {
    // 후보 고르기: 문법에 맞고, 형태소가 적고, 흔한 것.
    // kiwi 같은 언어 모형이 없으므로 이 셋이 잣대의 전부다.
    let best = null;
    const offer = (morphs, cut, rar) => {
      if (!chainOk(morphs)) return;
      const n = morphs.length;
      if (!best || n < best[3]
          || (n === best[3] && (cut > best[1]
              || (cut === best[1] && rar < best[2]))))
        best = [morphs, cut, rar, n];
    };
    for (let cut = core.length; cut >= 1; cut--) {
      const head = core.slice(0, cut), rest = core.slice(cut);
      // (a) 내용어 그대로
      const cands = KO_FORMS.get(head);
      if (cands) for (const [t] of cands) {
        if (GRAMMATICAL_KO.has(t)) continue;
        const tail = parseMarkers(rest);
        if (tail !== null)
          offer([[head, t], ...tail], cut, rarity("ko", head, t));
      }
      // (b) 활용 표면형 (부른 = 부르/VV + ᆫ/ETM)
      const infl = INFLECT.get(head);
      if (infl) for (const [mstr] of infl) {
        // 되지었을 때 같은 표면형이 나오는 갈래만 쓴다 — 그래야 되돌아온다
        const inv = INV_INFLECT.get(mstr);
        if (!inv || inv[0] !== head) continue;
        const morphs = mstr.split(" ").map(x => x.split("/"));
        const [hf, ht] = morphs[0];
        if (!KO.has(hf + "|" + ht)) continue;
        const tail = parseMarkers(rest);
        if (tail !== null)
          offer([...morphs, ...tail], cut, rarity("ko", hf, ht));
      }
    }
    // (c) 표지로만 이루어진 어절 (드묾)
    if (!best) {
      const only = parseMarkers(core);
      if (only && only.length) best = [only, 0, 0];
    }
    return best ? best[0] : null;
  }
  // 모음조화 이형태 — kiwi 는 었/어 로 눌러 적고 mecab 표는 았/아 를
  // 그대로 둔다. 두 표기를 잇는 다리.
  const ALLO = { "었/EP": "았/EP", "어/EC": "아/EC", "어서/EC": "아서/EC",
                 "었었/EP": "았었/EP" };
  function joinKo(morphs) {
    // 형태소열에서 어절을 되짓는다. parseEojeol 의 역.
    let out = "", i = 0;
    while (i < morphs.length) {
      let used = false;
      for (let j = Math.min(morphs.length, i + 4); j > i + 1; j--) {
        const parts = morphs.slice(i, j).map(m => m[0] + "/" + m[1]);
        let inv = INV_INFLECT.get(parts.join(" "));
        if (!inv) {
          const alt = parts.map(x => ALLO[x] || x);
          inv = INV_INFLECT.get(alt.join(" "));
        }
        if (inv) { out += inv[0]; i = j; used = true; break; }
      }
      if (!used) {
        const [f] = morphs[i];
        if (!SYL.test(f) && HANGUL.test(out.slice(-1))) return null; // 자모 융합 불가
        out += f; i++;
      }
    }
    return out;
  }

  const PARTICLE_ROLE = { JKS: "주어", JKO: "목적어", JKC: "보어",
    JKG: "관형어", JKB: "부사어", JKV: "독립어", JKQ: "부사어" };

  function classifyKo(chunks) {
    const n = chunks.length;
    for (const c of chunks) {
      const content = c.morphs.filter(m => !GRAMMATICAL_KO.has(m[1]) && m[1] !== "SYM");
      const head = content[content.length - 1];
      const has = (...tags) => c.morphs.some(m => tags.includes(m[1]));
      c.guessed = false;
      if (!head) { c.role = "부사어"; c.guessed = true; continue; }
      const tag = head[1];
      if (PRED_KO.has(tag) || has("XSV", "XSA")) {
        c.role = has("ETM") ? "관형어" : "서술어";
        if (has("ETN")) {
          const ps = c.morphs.filter(m => m[1].startsWith("JK") || m[1] === "JX");
          const p = ps[ps.length - 1];
          c.role = p ? (PARTICLE_ROLE[p[1]] || "목적어") : "목적어";
        }
        continue;
      }
      if (tag === "IC") { c.role = "독립어"; continue; }
      if (tag === "MM") { c.role = "관형어"; continue; }
      if (tag === "MAG" || tag === "MAJ") { c.role = "부사어"; continue; }
      if (has("VCP", "VCN")) { c.role = "서술어"; continue; }
      const ps = c.morphs.filter(m => m[1].startsWith("JK") || m[1] === "JX" || m[1] === "JC");
      const p = ps[ps.length - 1];
      if (p && PARTICLE_ROLE[p[1]]) { c.role = PARTICLE_ROLE[p[1]]; continue; }
      c.role = "주어"; c.guessed = true;
    }
    // 어림 손보기 — 밥은 내가 먹었다
    const expSubj = chunks.some(c => c.role === "주어" && !c.guessed);
    let expObj = chunks.some(c => c.role === "목적어" && !c.guessed);
    let usedSubj = expSubj;
    for (const c of chunks) {
      if (!c.guessed) continue;
      const content = c.morphs.filter(m => !GRAMMATICAL_KO.has(m[1]) && m[1] !== "SYM");
      const head = content[content.length - 1];
      if (!head || !SUBST_KO.has(head[1])) { c.role = "부사어"; continue; }
      if (expSubj) { c.role = expObj ? "부사어" : "목적어"; expObj = true; continue; }
      if (!usedSubj) { c.role = "주어"; usedSubj = true; continue; }
      if (!expObj) { c.role = "목적어"; expObj = true; } else c.role = "부사어";
    }
  }

  function analyzeKo(sentence) {
    const words = sentence.trim().split(/\s+/).filter(Boolean);
    const chunks = [];
    for (const w of words) {
      let core = w, punct = [];
      while (core && !HANGUL.test(core.slice(-1)) && !/[A-Za-z0-9]$/.test(core)) {
        punct.unshift(core.slice(-1)); core = core.slice(0, -1);
      }
      const parsed = core && HANGUL.test(core) ? parseEojeol(core) : null;
      const morphs = parsed || null;
      chunks.push({ surface: w, core, punct, morphs: morphs || [],
                    spell: !morphs });
    }
    classifyKo(chunks.map(c => c.morphs.length
      ? c : { ...c, morphs: [[c.core || c.surface, "NNG"]] }));
    // classifyKo가 자리(role)를 chunks에 그대로 썼는지 보정
    for (const c of chunks) if (!c.role) c.role = "부사어";
    // 되지어 보고 어긋나면 받아 적는다
    for (const c of chunks) {
      if (c.spell) continue;
      const back = joinKo(c.morphs);
      if (back !== c.core) c.spell = true;
    }
    return chunks;
  }

  /* ══ 영어 — 비터비 ══ */
  const TOKEN_RE = /[A-Za-z][A-Za-z'\-]*|\d+(?:[.,]\d+)?|[^\sA-Za-z\d]/g;
  const CONTRACT = ["n't", "'s", "'re", "'ve", "'ll", "'d", "'m"];
  const AUX = new Set(ET.aux), BE = new Set(ET.be), COP = new Set(ET.copula);
  const NOMINAL = new Set(ET.nominal), GRAM_EN = new Set(ET.grammatical);

  const IRR_PAST = { be:"was",become:"became",begin:"began","break":"broke",
    bring:"brought",build:"built",buy:"bought","catch":"caught",choose:"chose",
    come:"came","do":"did",draw:"drew",drink:"drank",drive:"drove",eat:"ate",
    fall:"fell",feel:"felt",find:"found",fly:"flew",forget:"forgot",get:"got",
    give:"gave",go:"went",grow:"grew",have:"had",hear:"heard",hold:"held",
    keep:"kept",know:"knew",leave:"left",lose:"lost",make:"made",meet:"met",
    pay:"paid",put:"put",read:"read",run:"ran",say:"said",see:"saw",sell:"sold",
    send:"sent",sing:"sang",sit:"sat",sleep:"slept",speak:"spoke",stand:"stood",
    take:"took",teach:"taught",tell:"told",think:"thought",
    understand:"understood",wear:"wore",win:"won",write:"wrote",shake:"shook",
    "throw":"threw",blow:"blew",ring:"rang",swim:"swam",rise:"rose",
    shine:"shone",hide:"hid",lie:"lay",lay:"laid",seek:"sought",spend:"spent",
    lend:"lent",bend:"bent",feed:"fed",lead:"led",hurt:"hurt",cost:"cost",
    cut:"cut",let:"let",set:"set",shut:"shut",hit:"hit",quit:"quit" };
  const PAST_TO_BASE = {}; Object.entries(IRR_PAST).forEach(([b, p]) => {
    if (!(p in PAST_TO_BASE)) PAST_TO_BASE[p] = b; });
  const IRR_PL = { child:"children",man:"men",woman:"women",person:"people",
    foot:"feet",tooth:"teeth",mouse:"mice",goose:"geese",life:"lives",
    leaf:"leaves",knife:"knives",wife:"wives" };
  const PL_TO_BASE = {}; Object.entries(IRR_PL).forEach(([b, p]) => PL_TO_BASE[p] = b);
  const V = "aeiou";
  const dbl = w => w.length >= 3 && !(V + "wxy").includes(w[w.length-1])
    && V.includes(w[w.length-2]) && !V.includes(w[w.length-3]);
  const addS = w => /(s|x|z|ch|sh)$/.test(w) ? w + "es"
    : (/[^aeiou]y$/.test(w) ? w.slice(0, -1) + "ies"
    : (/[^aeiou]o$/.test(w) ? w + "es" : w + "s"));
  function applyInf(w, g) {
    if (g === "«past»") {
      if (IRR_PAST[w]) return IRR_PAST[w];
      if (w.endsWith("e")) return w + "d";
      if (/[^aeiou]y$/.test(w)) return w.slice(0, -1) + "ied";
      if (dbl(w)) return w + w[w.length-1] + "ed";
      return w + "ed";
    }
    if (g === "«3sg»" || g === "«plural»") {
      if (g === "«plural»" && IRR_PL[w]) return IRR_PL[w];
      if (g === "«3sg»" && w === "be") return "is";
      if (g === "«3sg»" && w === "have") return "has";
      if (g === "«3sg»" && w === "do") return "does";
      return addS(w);
    }
    if (g === "«ing»") {
      if (w.endsWith("ie")) return w.slice(0, -2) + "ying";
      if (w.endsWith("e") && !w.endsWith("ee")) return w.slice(0, -1) + "ing";
      if (dbl(w)) return w + w[w.length-1] + "ing";
      return w + "ing";
    }
    return w;
  }
  function splitInf(w, tag, known) {
    const tryC = (base, gram) =>
      known(base, tag) && applyInf(base, gram) === w ? [base, gram] : null;
    if (tag === "VB") {
      if (PAST_TO_BASE[w] && known(PAST_TO_BASE[w], "VB"))
        return [PAST_TO_BASE[w], "«past»"];
      const cands = [];
      if (/ied$/.test(w) && w.length > 4) cands.push([w.slice(0,-3)+"y","«past»"]);
      if (/ed$/.test(w) && w.length > 3) {
        cands.push([w.slice(0,-2),"«past»"],[w.slice(0,-1),"«past»"]);
        if (w.length > 4 && w[w.length-3] === w[w.length-4])
          cands.push([w.slice(0,-3),"«past»"]);
      }
      if (/ing$/.test(w) && w.length > 4) {
        cands.push([w.slice(0,-3),"«ing»"],[w.slice(0,-3)+"e","«ing»"]);
        if (w.length > 5 && w[w.length-4] === w[w.length-5])
          cands.push([w.slice(0,-4),"«ing»"]);
      }
      if (/ies$/.test(w) && w.length > 4) cands.push([w.slice(0,-3)+"y","«3sg»"]);
      if (/es$/.test(w) && w.length > 3) cands.push([w.slice(0,-2),"«3sg»"]);
      if (/s$/.test(w) && !/ss$/.test(w) && w.length > 2)
        cands.push([w.slice(0,-1),"«3sg»"]);
      for (const [b, g] of cands) { const r = tryC(b, g); if (r) return r; }
    } else if (tag === "NN") {
      if (PL_TO_BASE[w] && known(PL_TO_BASE[w], "NN"))
        return [PL_TO_BASE[w], "«plural»"];
      const cands = [];
      if (/ies$/.test(w) && w.length > 4) cands.push(w.slice(0,-3)+"y");
      if (/es$/.test(w) && w.length > 3) cands.push(w.slice(0,-2));
      if (/s$/.test(w) && !/ss$/.test(w) && w.length > 2) cands.push(w.slice(0,-1));
      for (const b of cands)
        if (known(b, "NN") && applyInf(b, "«plural»") === w) return [b, "«plural»"];
    }
    return null;
  }

  const knownEn = (f, t) => { const s = EN_TAGS.get(f); return !!s && s.has(t); };
  function candidatesEn(w) {
    if (w && !/[a-z0-9]/.test(w[0])) return ["SYM"];
    const got = new Set(EN_TAGS.get(w) || []);
    // 굴절형의 잃어버린 읽기
    for (const [b, tags] of stemsEn(w))
      for (const t of tags) {
        const have = EN_TAGS.get(b);
        if (have && (have.has(t) || (t === "JJ" && have.has("VB")))) got.add(t);
      }
    const closed = ET.closed[w];
    if (closed) got.add(closed);
    if (AUX.has(w)) { got.add("VB"); got.add("MD"); }
    if (PAST_TO_BASE[w]) got.add("VB");
    if (got.size) return [...got].sort();
    if (/^\d/.test(w)) return ["CD"];
    for (const [suf, tag] of ET.suffix)
      if (w.endsWith(suf) && w.length > suf.length + 2) return [tag];
    return ["NN"];
  }
  function* stemsEn(w) {
    if (/ies$/.test(w) && w.length > 4) yield [w.slice(0,-3)+"y", ["VB","NN"]];
    if (/es$/.test(w) && w.length > 3) yield [w.slice(0,-2), ["VB","NN"]];
    if (/s$/.test(w) && !/ss$/.test(w) && w.length > 2) yield [w.slice(0,-1), ["VB","NN"]];
    if (/ed$/.test(w) && w.length > 3) {
      yield [w.slice(0,-2), ["VB","JJ"]]; yield [w.slice(0,-1), ["VB","JJ"]];
      if (w.length > 4 && w[w.length-3] === w[w.length-4]) yield [w.slice(0,-3), ["VB","JJ"]];
    }
    if (/ing$/.test(w) && w.length > 4) {
      yield [w.slice(0,-3), ["VB"]]; yield [w.slice(0,-3)+"e", ["VB"]];
      if (w.length > 5 && w[w.length-4] === w[w.length-5]) yield [w.slice(0,-4), ["VB"]];
    }
    if (/(er|est)$/.test(w) && w.length > 4) {
      const cut = w.endsWith("er") ? 2 : 3;
      yield [w.slice(0,-cut), ["JJ"]]; yield [w.slice(0,-cut)+"e", ["JJ"]];
    }
    if (/ly$/.test(w) && w.length > 4) yield [w.slice(0,-2), ["RB"]];
  }
  function emissionEn(w, t, first) {
    let sc = ET.prior[t] || 0;
    if (AUX.has(w)) { if (t === "VB" || t === "MD") sc += 8; }
    else if (ET.closed[w] === t) sc += 8;
    if (knownEn(w, t)) sc += 4;
    for (const [suf, guess] of ET.suffix)
      if (w.endsWith(suf) && w.length > suf.length + 2) {
        if (guess === t) sc += 3; break;
      }
    if (/ly$/.test(w) && t === "RB") sc += 4;
    if (/(er|est)$/.test(w) && t === "JJ") sc += 2;
    if (first && t === "VB") sc -= 2;
    if (t === "UH" && !first) sc -= 5;
    return sc;
  }
  function transEn(prev, prevWord, t) {
    const key = (prev === "VB" && BE.has(prevWord)) ? "BE" : prev;
    return (ET.trans[key] || {})[t] || 0;
  }
  function viterbiEn(words, cands) {
    const n = words.length, score = [], back = [];
    for (let i = 0; i < n; i++) {
      const cur = {}, bk = {};
      for (const t of cands[i]) {
        const em = emissionEn(words[i], t, i === 0);
        if (i === 0) { cur[t] = em + ((ET.trans["^"] || {})[t] || 0); bk[t] = "^"; }
        else {
          let bp = null, bs = -1e9;
          for (const [pt, ps] of Object.entries(score[i-1])) {
            const v = ps + transEn(pt, words[i-1], t);
            if (v > bs) { bp = pt; bs = v; }
          }
          cur[t] = em + bs; bk[t] = bp;
        }
      }
      score.push(cur); back.push(bk);
    }
    let bestT = null, bestS = -1e9;
    for (const [t, v] of Object.entries(score[n-1]))
      if (v > bestS) { bestT = t; bestS = v; }
    const tags = new Array(n); tags[n-1] = bestT;
    for (let i = n - 1; i > 0; i--) tags[i-1] = back[i][tags[i]];
    return [tags, bestS];
  }
  function tagEn(words) {
    const n = words.length;
    if (!n) return [];
    const cands = words.map(candidatesEn);
    let [tags] = viterbiEn(words, cands);
    if (!tags.some(t => t === "VB" || t === "MD")) {
      let best = tags, bestS = -1e9;
      for (let i = 0; i < n; i++) {
        if (!cands[i].includes("VB")) continue;
        const forced = cands.map((c, j) => j === i ? ["VB"] : c);
        const [got, sc] = viterbiEn(words, forced);
        if (sc > bestS) { best = got; bestS = sc; }
      }
      tags = best;
    }
    for (let i = 0; i < n; i++) {
      if (tags[i] === "VB" && AUX.has(words[i])) {
        const hasMain = tags.slice(i+1).some((t, j) =>
          t === "VB" && !AUX.has(words[i+1+j]));
        if (hasMain) tags[i] = "MD";
      }
      if (tags[i] === "MD" && AUX.has(words[i])) {
        const hasMain = tags.slice(i+1).some((t, j) =>
          t === "VB" && !AUX.has(words[i+1+j]));
        if (!hasMain) tags[i] = "VB";
      }
    }
    for (let i = 2; i < n; i++)
      if (tags[i-1] === "CC" && ["JJ","RB","NN"].includes(tags[i-2])
          && cands[i].includes(tags[i-2])) tags[i] = tags[i-2];
    if (n >= 2 && tags[n-1] === "VB" && cands[n-1].includes("JJ")
        && tags.slice(0,-1).some(t => t === "VB")) tags[n-1] = "JJ";
    return tags;
  }
  function rolesEn(words, tags) {
    const n = words.length, roles = new Array(n).fill("부사어");
    let verb = null;
    for (let i = 0; i < n; i++)
      if (tags[i] === "VB" && (i === 0 || tags[i-1] !== "TO")) { verb = i; break; }
    if (verb === null) for (let i = 0; i < n; i++)
      if (tags[i] === "MD") { verb = i; break; }
    const copula = verb !== null && COP.has(words[verb]);
    const inverted = n > 0 && (tags[0] === "MD"
      || (tags[0] === "WP" && n > 1 && ["MD","VB"].includes(tags[1])));
    const head = new Array(n).fill(false);
    let i = 0;
    while (i < n) {
      if (NOMINAL.has(tags[i])) {
        let j = i;
        while (j + 1 < n && NOMINAL.has(tags[j+1])) j++;
        head[j] = true; i = j + 1;
      } else i++;
    }
    let prep = false, subjTaken = false;
    for (let i = 0; i < n; i++) {
      const t = tags[i];
      if (t === "UH") roles[i] = "독립어";
      else if (t === "SYM") roles[i] = "표지";
      else if (GRAM_EN.has(t)) { roles[i] = "표지"; if (t === "IN") prep = true; }
      else if (t === "RB") roles[i] = "부사어";
      else if (t === "VB") { roles[i] = "서술어"; prep = false; }
      else if (t === "JJ" || t === "CD") {
        const nxt = tags[i+1];
        if (NOMINAL.has(nxt) || nxt === "JJ" || nxt === "CD") roles[i] = "관형어";
        else if (copula && verb !== null && i > verb) roles[i] = "보어";
        else roles[i] = "관형어";
      } else if (NOMINAL.has(t)) {
        if (t === "WP" && i === 0)
          roles[i] = ["who","what"].includes(words[i]) ? "주어" : "부사어";
        else if (!head[i]) roles[i] = "관형어";
        else if (prep) roles[i] = "부사어";
        else if (verb === null) roles[i] = i === 0 ? "주어" : "목적어";
        else if (inverted && !subjTaken) { roles[i] = "주어"; subjTaken = true; }
        else if (i < verb) { roles[i] = "주어"; subjTaken = true; }
        else roles[i] = copula ? "보어" : "목적어";
        if (head[i]) prep = false;
      }
    }
    return roles;
  }
  function analyzeEn(sentence) {
    const words = [], raws = [], groups = [];
    let gi = -1;
    for (const rawWord of sentence.trim().split(/\s+/)) {
      gi++;
      for (const piece of rawWord.match(TOKEN_RE) || []) {
        if (/[.?!…]/.test(piece) && piece.length === 1) continue;
        const low = piece.toLowerCase();
        let cut = null;
        for (const c of CONTRACT)
          if (low.endsWith(c) && low.length > c.length) { cut = c; break; }
        if (cut) {
          words.push(low.slice(0, -cut.length)); raws.push(piece.slice(0, -cut.length)); groups.push(gi);
          words.push(cut); raws.push(piece.slice(-cut.length)); groups.push(gi);
        } else { words.push(low); raws.push(piece); groups.push(gi); }
      }
    }
    if (!words.length) return [];
    const tags = tagEn(words);
    const roles = rolesEn(words, tags);
    const toks = [];
    for (let i = 0; i < words.length; i++) {
      const w = words[i], t = tags[i];
      const piece = (t === "VB" || t === "NN") ? splitInf(w, t, knownEn) : null;
      if (piece) {
        toks.push({ form: piece[0], tag: t, role: roles[i], group: groups[i], raw: raws[i] });
        toks.push({ form: piece[1], tag: "GRAM", role: "표지", group: groups[i], raw: "" });
      } else toks.push({ form: w, tag: t, role: roles[i], group: groups[i], raw: raws[i] });
    }
    return toks;
  }
  function joinEn(toks) {
    // 원형(form)에서 표면형을 되짓는다. raw 를 쓰면 이미 활용된 꼴에
    // 또 활용을 겹치게 된다.
    const cap = (f, raw) => /^[A-Z]/.test(raw || "")
      ? f[0].toUpperCase() + f.slice(1) : f;
    const out = []; let cur = "", g0 = null;
    for (const t of toks) {
      if (t.tag === "GRAM") {
        const low = cur.toLowerCase();
        const inf = applyInf(low, t.form);
        cur = cur && /^[A-Z]/.test(cur) ? inf[0].toUpperCase() + inf.slice(1) : inf;
        continue;
      }
      const f = cap(t.form, t.raw);
      if (g0 === null) { cur = f; g0 = t.group; }
      else if (t.group !== g0) { out.push(cur); cur = f; g0 = t.group; }
      else cur += f;
    }
    if (cur) out.push(cur);
    return out.join(" ");
  }

  /* ══ 작곡 ══ */
  function spellGlyphs(lang, roleIdx, text, closeAtEnd, flag) {
    const alpha = D.alphabet[lang];
    const out = [];
    const chars = [...text].filter(ch => alpha.indexOf(ch) >= 0);
    if (!chars.length) chars.push("?");
    chars.forEach((ch, j) => {
      out.push({ roleIdx, kind: 2, lang, tier: -1, qi: 2,
                 index: alpha.indexOf(ch),
                 close: j === chars.length - 1 ? closeAtEnd : 0,
                 flag: j === 0 ? flag : 0, pol: 0,
                 label: "글자 " + ch });
    });
    return out;
  }

  function composeSentence(lang, sentence, term) {
    const glyphs = [];   // {roleIdx,kind,lang,tier,qi,index,close,flag,pol,label}
    const analysis = [];
    let wordRef = () => -1;
    const push = (...gs) => glyphs.push(...gs.map(g => (g.word = wordIdx, g)));

    let wordIdx = -1;
    const stamp = g => { g.word = wordIdx; return g; };
    if (lang === "ko") {
      const chunks = analyzeKo(sentence);
      for (const c of chunks) {
        wordIdx++;
        analysis.push({ surface: c.surface, role: c.role,
          morphs: c.spell ? [[c.core || c.surface, "받아적기"]] : c.morphs,
          spelled: c.spell });
        const roleIdx = R_IDX[c.role];
        if (c.spell) {
          push(...spellGlyphs("ko", roleIdx, c.surface, 1, 0));
          continue;
        }
        const parts = [...c.morphs.map(m => ({ m, punct: false })),
                       ...c.punct.map(p => ({ m: [p, "SYM"], punct: true }))];
        parts.forEach((part, j) => {
          const [f, t] = part.m;
          const close = j === parts.length - 1 ? 1 : 0;
          const rIdx = GRAMMATICAL_KO.has(t) || t === "SYM"
            ? R_IDX["표지"] : roleIdx;
          const ci = CONCEPT_KO.get(f + "|" + t);
          const entry = KO.get(f + "|" + t);
          if (ci !== undefined) {
            const c2 = D.concepts[ci];
            push({ roleIdx: rIdx, kind: 0, lang: null,
                   tier: conceptTier(ci), qi: conceptQi(ci), index: ci,
                   close, flag: 0, pol: c2[5],
                   label: `${f}/${t} ≡${c2[0]}↔${c2[2]}` });
          } else if (entry) {
            push({ roleIdx: rIdx, kind: 1, lang: "ko",
                   tier: entry[0], qi: entry[1], index: entry[2],
                   close, flag: 0, pol: entry[3], label: `${f}/${t}` });
          } else {
            push(...spellGlyphs("ko", rIdx, f, close, 0));
          }
        });
      }
    } else {
      const toks = analyzeEn(sentence);
      // 되지어 어긋나면 어절 통째 받아 적는다
      const byGroup = new Map();
      for (const t of toks) {
        if (!byGroup.has(t.group)) byGroup.set(t.group, []);
        byGroup.get(t.group).push(t);
      }
      for (const [g, group] of byGroup) {
        wordIdx++;
        const surface = group.map(t => t.raw).join("");
        const back = joinEn(group);
        const contentRoles = group.filter(t => t.role !== "표지");
        const role = contentRoles.length ? contentRoles[0].role : "표지";
        const spell = back !== surface;
        analysis.push({ surface, role,
          morphs: spell ? [[surface, "받아적기"]]
                        : group.map(t => [t.form, t.tag]),
          spelled: spell });
        if (spell) {
          push(...spellGlyphs("en", R_IDX[role], surface, 1,
                              /[A-Z]/.test(surface[0]) ? 1 : 0));
          continue;
        }
        group.forEach((t, j) => {
          const close = j === group.length - 1 ? 1 : 0;
          const rIdx = R_IDX[t.role];
          const flag = /^[A-Z]/.test(t.raw) ? 1 : 0;
          const ci = CONCEPT_EN.get(t.form + "|" + t.tag);
          const entry = EN.get(t.form + "|" + t.tag);
          if (ci !== undefined) {
            const c2 = D.concepts[ci];
            push({ roleIdx: rIdx, kind: 0, lang: null,
                   tier: conceptTier(ci), qi: conceptQi(ci), index: ci,
                   close, flag, pol: c2[5],
                   label: `${t.form}/${t.tag} ≡${c2[0]}↔${c2[2]}` });
          } else if (entry) {
            push({ roleIdx: rIdx, kind: 1, lang: "en",
                   tier: entry[0], qi: entry[1], index: entry[2],
                   close, flag, pol: entry[3], label: `${t.form}/${t.tag}` });
          } else {
            push(...spellGlyphs("en", rIdx, t.raw || t.form, close, flag));
          }
        });
      }
    }
    return { glyphs, analysis, term };
  }

  function conceptTier(ci) {
    return D.concepts[ci][4];
  }
  function conceptQi(ci) {
    const p = D.concepts[ci][5];
    return p > 0 ? 0 : p < 0 ? 1 : 2;
  }

  function compose(text, lang) {
    // 문장 가르기
    const parts = text.trim().split(/(?<=[.?!…])\s+/).filter(s => s.trim());
    const sentences = [];
    const notes = [];
    let cursor = 0;
    for (const raw of parts) {
      const m = raw.match(/[.?!…]+$/);
      const term = m ? m[0][0] : ".";
      const body = raw.replace(/[.?!…]+$/, "");
      const s = composeSentence(lang, body, term);
      // 소리로 편다
      const sNotes = [];
      for (const g of s.glyphs) {
        const ev = encodeGlyph(g.roleIdx, g.kind, g.lang, g.tier, g.qi,
                               g.index, g.close, g.flag, g.pol);
        for (const e of ev) {
          sNotes.push({ p: e.p, s: cursor, d: e.d, v: e.v, slot: e.slot,
                        src: g.label, role: K.roles[g.roleIdx],
                        w: g.word, si: sentences.length,
                        kind: g.kind, qi: g.qi, tier: g.tier,
                        idx: g.index });
          cursor += e.d + e.rest;
        }
      }
      const t = terminatorEvent(term);
      sNotes.push({ p: t.p, s: cursor, d: t.d, v: t.v, slot: "종결",
                    src: "종결 " + term, role: "맺음",
                    w: -1, si: sentences.length, kind: -1 });
      cursor += t.d + t.rest;
      notes.push(...sNotes);
      sentences.push(s);
    }
    // 글리프 번호 다시 매기기 (피아노롤 띠용)
    let gi = -1, lastSrc = null;
    for (const n of notes) {
      if (n.slot === "역할" || (n.slot === "받아적기" && n.src !== lastSrc)
          || n.slot === "종결") gi++;
      lastSrc = n.src;
      n.g = n.slot === "종결" ? -1 : gi;
    }
    const allGlyphs = sentences.flatMap(s => s.glyphs);
    const content = allGlyphs.filter(g => K.roles[g.roleIdx] !== "표지");
    const translatable = content.length
      ? content.filter(g => g.kind === 0).length / content.length : 1;
    return { lang, sentences, notes, translatable,
             chords: notes.map(n => n.p) };
  }

  /* ══ 소리 빚기 — 파이썬 wave_out 과 같은 잣대 ══ */
  const SR = 44100, PARTIALS = [[1,1],[2,.28],[3,.14],[4,.06]];
  const ATTACK = .012, REL = .06, GAP = .13, MIN_DUR = .30;
  function schedule(notes, tempo) {
    // (시작초, 길이초, 원래 note) — 재생과 시각화가 같은 시계를 쓴다
    const unit = 60 / (tempo || 72) / 4;
    const out = [];
    let t = 0;
    for (const n of [...notes].sort((a, b) => a.s - b.s)) {
      const dur = Math.max(MIN_DUR, n.d * unit);
      out.push([t, dur, n]);
      t += dur + GAP;
    }
    return out;
  }

  function synth(notes, tempo) {
    const sched = schedule(notes, tempo).map(([t, dur, n]) => [t, dur, n.p, n.v]);
    const last = sched[sched.length - 1];
    const total = Math.ceil((last[0] + last[1] + REL + .3) * SR);
    const buf = new Float64Array(total);
    for (const [start, hold, pitches, vel] of sched) {
      const t0 = Math.round(start * SR);
      const count = Math.round((hold + REL) * SR);
      const amp = Math.pow(vel / 127, 1.6) * .22 / Math.max(1, pitches.length);
      for (const p of pitches) {
        const w = 2 * Math.PI * 440 * Math.pow(2, (p - 69) / 12) / SR;
        for (let i = 0; i < count; i++) {
          const tt = i / SR;
          let env;
          if (tt < ATTACK) env = tt / ATTACK;
          else if (tt < hold) env = 1 - .25 * (tt - ATTACK) / Math.max(1e-6, hold - ATTACK);
          else {
            env = .75 * Math.exp(-(tt - hold) * 60);
            if (env <= .0005) break;
          }
          let v = 0;
          for (const [k, g] of PARTIALS) v += g * Math.sin(w * k * i);
          const j = t0 + i;
          if (j < total) buf[j] += amp * env * v;
        }
      }
    }
    let peak = 0;
    for (let i = 0; i < total; i++) peak = Math.max(peak, Math.abs(buf[i]));
    const gain = peak > 0 ? .89 / peak : 1;
    const pcm = new Int16Array(total);
    for (let i = 0; i < total; i++)
      pcm[i] = Math.max(-32768, Math.min(32767, Math.round(buf[i] * gain * 32767)));
    return pcm;
  }
  function wavBlob(pcm) {
    const n = pcm.length, size = 44 + n * 2;
    const b = new ArrayBuffer(size), v = new DataView(b);
    const str = (o, s) => { for (let i = 0; i < s.length; i++) v.setUint8(o + i, s.charCodeAt(i)); };
    str(0, "RIFF"); v.setUint32(4, size - 8, true); str(8, "WAVE");
    str(12, "fmt "); v.setUint32(16, 16, true); v.setUint16(20, 1, true);
    v.setUint16(22, 1, true); v.setUint32(24, SR, true);
    v.setUint32(28, SR * 2, true); v.setUint16(32, 2, true);
    v.setUint16(34, 16, true); str(36, "data"); v.setUint32(40, n * 2, true);
    new Int16Array(b, 44).set(pcm);
    return new Blob([b], { type: "audio/wav" });
  }

  function entryOf(lang, form, tag) {
    const e = (lang === "ko" ? KO : EN).get(form + "|" + tag);
    return e || null;
  }
  function lookupRev(lang, tier, quality, index) {
    const rev = lang === "ko" ? KO_REV : EN_REV;
    const v = rev.get(tier + "/" + quality + "/" + index);
    return v ? v.split("|") : null;
  }
  function isConcept(lang, form, tag) {
    return (lang === "ko" ? CONCEPT_KO : CONCEPT_EN).has(form + "|" + tag);
  }
  function inDict(lang, form, tag) {
    return (lang === "ko" ? KO : EN).has(form + "|" + tag);
  }
  function approxOf(lang, form, tag) {
    const exact = (lang === "ko" ? CONCEPT_KO : CONCEPT_EN).get(form + "|" + tag);
    if (exact !== undefined) return exact;
    const a = APPROX.get(lang + "|" + form + "|" + tag);
    return a !== undefined ? a : null;
  }

  window.SoriWrite = { compose, analyzeKo, analyzeEn, joinKo, joinEn,
                       synth, wavBlob, schedule, SR, lookupRev, approxOf,
                       isConcept, inDict, entryOf, encodeGlyph,
                       terminatorEvent,
                       detect: t => /[가-힣ᄀ-ᇿ]/.test(t) ? "ko" : "en" };
})();
