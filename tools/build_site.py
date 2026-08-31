#!/usr/bin/env python3
"""웹페이지가 쓸 자료를 만든다.

브라우저에서도 **되읽기**는 그대로 된다. 되읽기에는 형태소 분석기가
필요 없고 화음 은행과 개념표만 있으면 되기 때문이다. 그래서 페이지는
소리를 넣으면 한국어와 영어로 내어 준다.

다만 한국어 활용(아름답 + ㄴ → 아름다운)은 브라우저에서 지을 수 없으므로,
자리마다 필요한 꼴을 여기서 미리 지어 실어 보낸다.

내는 것: docs/data.js
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from sorimun.compose import Composer  # noqa: E402
from sorimun.concepts import Concepts  # noqa: E402
from sorimun.core import codes as C, pitch  # noqa: E402
from sorimun.core.banks import BANKS  # noqa: E402
from sorimun.core.glyph import Kind  # noqa: E402
from sorimun.core.harmony import Quality  # noqa: E402
from sorimun.core.roles import ENGLISH_NAME, ORDER as ROLES  # noqa: E402
from sorimun.decompose import read, render  # noqa: E402
from sorimun.dictionary import TIER_LABEL, TIER_LABEL_EN  # noqa: E402
from sorimun.generate import _korean_one  # noqa: E402
from sorimun.lang import get, inflect_en as INF  # noqa: E402

OUT = ROOT / "docs" / "data.js"

EXAMPLES = [
    ("ko", "아이가 조용히 웃었다.",
     "일곱 자리 가운데 셋이 나온다. 소리에는 '아이·웃다·과거·조용히' 라는 "
     "개념만 담기고 조사와 어미는 담기지 않는다. 그래서 영어로도 읽힌다."),
    ("en", "The child laughed quietly.",
     "위와 똑같은 소리다. 영어로 적었지만 소리는 같은 개념을 담으므로 "
     "한국어로 읽어 내면 '아이가 조용히 웃었다' 가 나온다."),
    ("ko", "바람이 꽃을 흔들었다.",
     "주어·목적어·서술어가 모두 개념으로 적힌다. 자리는 역할 화음이, "
     "뜻은 의미 화음과 자릿 화음이 나른다."),
    ("en", "The water was dark.",
     "영어의 'was' 는 한국어에 없다. 그래서 소리에 담기지 않고, 과거라는 "
     "개념만 담긴다. 한국어로 읽으면 '어두웠다' 로 되살아난다."),
    ("ko", "아름다운 노래가 어두운 밤을 천천히 어루만졌다.",
     "'어루만지다' 는 개념표에 없어 한국어 전용으로 적힌다. 그런 낱말은 "
     "다른 말로 옮겨지지 않는다 — 소리에 옮겨진 몫이 표시된다."),
    ("ko", "쀍뿕뿅이 우두두두 쏟아졌다.",
     "사전에도 없는 말은 글자를 하나씩 받아 적는다. 길고 더듬거리지만 "
     "글자 하나 틀리지 않고 돌아온다."),
    ("en", "Love is stronger than death.",
     "비교급과 전치사는 영어의 것이라 소리에 담기지 않는다. 개념으로 "
     "옮겨진 몫이 낮아지는 것이 그대로 드러난다."),
    ("en", "Zxqwv frobnicates the widget.",
     "사전에 없는 영어 낱말도 글자로 받아 적힌다."),
]


# 체언은 받침만 보면 조사를 붙일 수 있으므로 브라우저가 짓는다.
# 활용이 필요한 용언만 미리 지어 실어 보낸다.
_PREDICATE_TAGS = {"VV", "VA", "VX", "VCP", "VCN", "XR"}


def korean_forms(c, kiwi):
    """활용이 필요한 낱말만, 자리마다의 꼴을 미리 지어 둔다."""
    if c.ko_tag not in _PREDICATE_TAGS:
        return None
    from sorimun.core.roles import Role
    return {
        "p": _korean_one(c.ko_form, c.ko_tag, Role.PREDICATE, kiwi, []),
        "pp": _korean_one(c.ko_form, c.ko_tag, Role.PREDICATE, kiwi, [INF.PAST]),
        "a": _korean_one(c.ko_form, c.ko_tag, Role.ADNOMINAL, kiwi, []),
        "ap": _korean_one(c.ko_form, c.ko_tag, Role.ADNOMINAL, kiwi, [INF.PAST]),
        "v": _korean_one(c.ko_form, c.ko_tag, Role.ADVERBIAL, kiwi, []),
    }


def main() -> int:
    ka, ea = get("ko"), get("en")
    kiwi = getattr(ka, "_kiwi", None)
    cx = Concepts.load()

    examples = []
    for lang, text, note in EXAMPLES:
        an = ka if lang == "ko" else ea
        p = Composer(lang, analyzer=an).compose(an.analyze(text))
        r = read(p.chords)
        examples.append({
            "lang": lang, "text": text, "note": note,
            "tempo": p.tempo,
            "translatable": round(p.translatable, 3),
            "ko": render(r, "ko", ka),
            "en": render(r, "en", ea),
            "tokens": [
                {"form": t.form, "tag": t.tag, "role": t.role.value,
                 "group": t.group}
                for t in p.analysis.tokens
            ],
            "notes": [
                {"p": list(n.pitches), "s": n.start, "d": n.duration,
                 "v": n.velocity, "slot": n.slot, "src": n.source,
                 "role": n.role, "g": n.glyph}
                for n in sorted(p.notes, key=lambda x: x.start)
            ],
            "glyphs": [
                {"role": g.role.value, "kind": g.kind.value,
                 "lang": g.lang, "tier": g.tier,
                 "quality": g.quality.value, "index": g.index,
                 "label": lab}
                for g, lab in zip(p.glyphs, p.labels)
            ],
        })

    banks = {
        "role": [list(BANKS.role[i].voicing) for i in range(8)],
        "meaning": {f"{t}/{q.value}": list(BANKS.meaning[(t, q)].voicing)
                    for t in range(6) for q in Quality},
        "language": {k: list(v.voicing) for k, v in BANKS.language.items()},
        "letter": {k: list(v.voicing) for k, v in BANKS.letter.items()},
        "digit": {q.value: [list(s.voicing) for s in v]
                  for q, v in BANKS.digit.items()},
        "close": [list(s.voicing) for s in BANKS.close],
        "term": [list(s.voicing) for s in BANKS.term],
    }

    codes = {
        "roles": [r.value for r in ROLES],
        "rolesEn": [ENGLISH_NAME[r] for r in ROLES],
        "rolePitch": [C.ROLE_PITCH[r] for r in ROLES],
        "band": [C.BAND[r] for r in ROLES],
        "flagOffsets": list(C.FLAG_OFFSETS),
        "digitOffsets": list(C.DIGIT_OFFSETS),
        "base": C.BASE,
        "terminators": list(C.TERMINATORS),
        "lowest": pitch.LOWEST, "highest": pitch.HIGHEST,
        "tierLabel": list(TIER_LABEL), "tierLabelEn": list(TIER_LABEL_EN),
    }

    # 개념표 — 되읽기와 생성에 필요한 것만
    # 자리를 아끼려고 배열로 싣는다: [한국어, 품사, 영어, 품사, 등급, 극성, 활용]
    concepts = []
    for c in cx.all:
        f = korean_forms(c, kiwi)
        row = [c.ko_form, c.ko_tag, c.en_form, c.en_tag, c.tier, c.polarity]
        if f:
            row.append([f["p"], f["pp"], f["a"], f["ap"], f["v"]])
        concepts.append(row)

    from sorimun.core import alphabet
    payload = {
        "codes": codes, "banks": banks, "examples": examples,
        "concepts": concepts,
        "alphabet": {k: "".join(v) for k, v in alphabet.ALPHABET.items()},
        "meta": {
            "concepts": len(cx),
            "ko": 286068, "en": 260000,
            "reserved": len(BANKS.all_shapes()),
        },
    }
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(
        "window.SORIMUN = "
        + json.dumps(payload, ensure_ascii=False, separators=(",", ":"))
        + ";\n", encoding="utf-8")
    print(f"→ {OUT.relative_to(ROOT)} ({OUT.stat().st_size:,}B)")
    print(f"  예제 {len(examples)}개, 개념 {len(concepts):,}개")
    return 0


if __name__ == "__main__":
    sys.exit(main())
