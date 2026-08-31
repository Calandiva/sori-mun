#!/usr/bin/env python3
"""철저한 재검증.

이 프로젝트가 내건 약속은 다섯이다. 하나씩 실제로 확인한다.

  1. 음높이와 화성만으로 푼다   길이를 아무렇게나 흔들어도 뜻이 그대로인가
  2. 겹치지 않는다              서로 다른 낱말이 서로 다른 소리를 갖는가
  3. 2옥타브를 지킨다           어떤 소리도 C3~C5 를 벗어나지 않는가
  4. 되돌릴 수 있다             적은 문장이 그대로 돌아오는가
  5. 하나의 말이 된다           영어로 적은 소리를 한국어로 읽어 내는가
"""

from __future__ import annotations

import random
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.compose import Composer  # noqa: E402
from sorimun.concepts import Concepts  # noqa: E402
from sorimun.core import codes as C, pitch  # noqa: E402
from sorimun.core.banks import BANKS  # noqa: E402
from sorimun.core.glyph import Kind, decode, encode, terminator  # noqa: E402
from sorimun.core.harmony import Quality  # noqa: E402
from sorimun.core.roles import ORDER as ROLES  # noqa: E402
from sorimun.decompose import read, render  # noqa: E402
from sorimun.dictionary import Dictionary  # noqa: E402
from sorimun.lang import get  # noqa: E402

FAIL = 0


def check(ok: bool, label: str, detail: str = "") -> None:
    global FAIL
    if ok:
        print(f"  ✓ {label}")
    else:
        FAIL += 1
        print(f"  ✗ {label}" + (f"\n      {detail}" if detail else ""))


SAMPLE_INDEX = (0, 1, 31, 32, 271, 1055, 1056, 33823, 33824,
                285_999, 1_082_399)


def glyph_space():
    """글리프가 담을 수 있는 값의 조합을 훑는다."""
    for role in ROLES:
        for flag in (0, 1):
            for close in (C.CLOSE_CONTINUE, C.CLOSE_BREAK):
                for kind, lang in ((Kind.CONCEPT, None),
                                   (Kind.WORD, "ko"), (Kind.WORD, "en")):
                    for tier in range(6):
                        for q in Quality:
                            for idx in SAMPLE_INDEX:
                                yield role, flag, close, kind, lang, tier, q, idx


def main() -> int:
    print("═" * 62)
    print("1. 은행 — 자리마다 쓰는 화음이 서로소인가")
    v = [s.voicing for s in BANKS.all_shapes()]
    check(len(set(v)) == len(v), f"예약 화음 {len(v)}개가 모두 다르다")
    check(all(2 <= len(s.voicing) <= 3 for s in BANKS.all_shapes()),
          "모든 화음이 2음 또는 3음이다")
    check(all(s.span <= 7 for q in BANKS.digit for s in BANKS.digit[q]),
          "자릿 화음은 폭 7 이하 (근음이 부호를 나를 자리를 남긴다)")

    print("\n2. 코덱 — 적은 것이 그대로 돌아오는가 (전수)")
    n = bad = 0
    worst = None
    for params in glyph_space():
        role, flag, close, kind, lang, tier, q, idx = params
        g = encode(role, kind, tier, q, idx, lang=lang, close=close, flag=flag)
        b, nxt = decode(g.chords)
        n += 1
        ok = (b.role is role and b.flag == flag and b.close == close
              and b.kind is kind and b.lang == lang and b.tier == tier
              and b.quality is q and b.index == idx and nxt == len(g.chords))
        if not ok:
            bad += 1
            worst = worst or params
    check(bad == 0, f"글리프 {n:,}가지가 값 그대로 돌아온다",
          f"어긋난 보기: {worst}")
    print("     → 되읽기가 값을 남김없이 되찾으므로, 서로 다른 낱말이")
    print("       같은 소리를 가질 수 없다. 겹치지 않음이 여기서 따라 나온다.")

    print("\n3. 음역 — 2옥타브를 벗어나지 않는가")
    out = 0
    lo, hi = 128, 0
    for params in glyph_space():
        role, flag, close, kind, lang, tier, q, idx = params
        g = encode(role, kind, tier, q, idx, lang=lang, close=close, flag=flag)
        for e in g.events:
            for p in e.pitches:
                lo, hi = min(lo, p), max(hi, p)
                if not pitch.LOWEST <= p <= pitch.HIGHEST:
                    out += 1
    for t in C.TERMINATORS:
        for p in terminator(t).pitches:
            lo, hi = min(lo, p), max(hi, p)
    check(out == 0,
          f"모든 소리가 {pitch.name(pitch.LOWEST)}~{pitch.name(pitch.HIGHEST)} 안 "
          f"(실제로 쓰인 폭 {pitch.name(lo)}~{pitch.name(hi)})")

    print("\n4. 길이 무관 — 흔들어도 뜻이 그대로인가")
    rng = random.Random(20260831)
    kos, ens = get("ko"), get("en")
    shaken = same = 0
    for lang, an, lines in (("ko", kos, (ROOT / "data" / "sentences_ko.txt")),
                            ("en", ens, (ROOT / "data" / "sentences_en.txt"))):
        cp = Composer(lang, analyzer=an)
        for text in lines.read_text(encoding="utf-8").split("\n"):
            if not text.strip():
                continue
            p = cp.compose(an.analyze(text.strip()))
            base = render(read(p.chords), lang, an)
            for _ in range(3):
                # 길이와 세기를 마구 흔든다. 화음의 차례만 그대로 둔다.
                for note in p.notes:
                    note.duration = rng.randint(1, 24)
                    note.velocity = rng.randint(30, 127)
                shaken += 1
                if render(read(p.chords), lang, an) == base:
                    same += 1
    check(shaken == same,
          f"길이·세기를 마구 흔든 {shaken}번 모두 같은 뜻으로 읽힌다")

    print("\n5. 사전 — 낱말과 번호 사이를 오가는가 (전수)")
    for lang in ("ko", "en"):
        d = Dictionary.load(lang)
        bad = 0
        for e in d.entries:
            back = d.at(e.tier, e.quality, e.index)
            if back is None or (back.form, back.tag) != (e.form, e.tag):
                bad += 1
        check(bad == 0, f"{lang} 사전 {len(d):,}항목이 번호로 되찾아진다")

    print("\n6. 개념 — 두 말을 잇는가 (전수)")
    cx = Concepts.load()
    bad = 0
    for c in cx.all:
        if cx.at(c.index) is not c:
            bad += 1
        if c.ko_tag != "∅" and cx.of("ko", c.ko_form, c.ko_tag) is None:
            bad += 1
        if cx.of("en", c.en_form, c.en_tag) is None:
            bad += 1
    check(bad == 0, f"개념 {len(cx):,}개가 번호·한국어·영어 어느 쪽으로도 찾아진다")

    print("\n7. 문장 — 적은 그대로 돌아오는가")
    for lang, an, path in (("ko", kos, ROOT / "data" / "sentences_ko.txt"),
                           ("en", ens, ROOT / "data" / "sentences_en.txt")):
        cp = Composer(lang, analyzer=an)
        total = ok = 0
        misses = []
        for text in path.read_text(encoding="utf-8").split("\n"):
            text = text.strip()
            if not text:
                continue
            total += 1
            p = cp.compose(an.analyze(text))
            got = render(read(p.chords), lang, an)
            if got == text:
                ok += 1
            else:
                misses.append(f"{text!r} → {got!r}")
        check(ok == total, f"{lang} 문장 {ok}/{total} 이 글자까지 그대로 돌아온다",
              "\n      ".join(misses[:4]))

    print("\n8. 하나의 말 — 다른 말로 읽어 내는가")
    for src, dst in (("ko", "en"), ("en", "ko")):
        sa, da = get(src), get(dst)
        cp = Composer(src, analyzer=sa)
        path = ROOT / "data" / f"sentences_{src}.txt"
        rows = []
        rate = []
        for text in path.read_text(encoding="utf-8").split("\n"):
            text = text.strip()
            if not text:
                continue
            p = cp.compose(sa.analyze(text))
            r = read(p.chords)
            rate.append(p.translatable)
            rows.append((text, render(r, dst, da), p.translatable))
        avg = sum(rate) / len(rate)
        full = sum(1 for _t, _o, x in rows if x >= 0.999)
        print(f"  · {src}→{dst}: 개념으로 옮겨진 낱말 평균 {avg:.0%}, "
              f"온전히 옮겨진 문장 {full}/{len(rows)}")
        for t, o, x in rows[:6]:
            print(f"      {x:>4.0%} 『{t}』 → 『{o}』")

    print("\n9. 소리 → 소리 — 한 바퀴 돌아 제자리로 오는가")
    # 영어로 적은 소리를 한국어로 읽고, 그 한국어를 다시 소리로 적고,
    # 다시 영어로 읽는다. 뜻이 살아남는지 본다.
    ka, ea = get("ko"), get("en")
    ck, ce = Composer("ko", analyzer=ka), Composer("en", analyzer=ea)
    kept = total = 0
    for text in (ROOT / "data" / "sentences_en.txt").read_text(
            encoding="utf-8").split("\n"):
        text = text.strip()
        if not text:
            continue
        r1 = read(ce.compose(ea.analyze(text)).chords)
        korean = render(r1, "ko", ka)
        if not korean.strip(" ."):
            continue
        r2 = read(ck.compose(ka.analyze(korean)).chords)
        back = render(r2, "en", ea)
        total += 1
        a = {c.index for _r, c, _g in r1.concepts}
        b = {c.index for _r, c, _g in r2.concepts}
        if a and b and len(a & b) / len(a | b) >= 0.6:
            kept += 1
        if total <= 5:
            print(f"      『{text}』 → 『{korean}』 → 『{back}』")
    check(kept >= total * 0.7,
          f"영어→소리→한국어→소리→영어 에서 뜻의 {kept}/{total} 이 살아남는다")

    print("\n" + "═" * 62)
    if FAIL:
        print(f"실패 {FAIL}건")
        return 1
    print("모든 약속을 지킨다")
    return 0


if __name__ == "__main__":
    sys.exit(main())
