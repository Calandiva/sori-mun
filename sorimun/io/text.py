"""터미널에 보여 주는 표."""

from __future__ import annotations

from ..compose import Piece
from ..concepts import Concepts
from ..core import codes as C, pitch
from ..core.glyph import Kind
from ..core.roles import ENGLISH_NAME, Role
from ..decompose import Reading
from ..dictionary import TIER_LABEL

SLOT_MARK = {"역할": "자리", "언어": "말", "받아적기": "받아적기",
             "서명": "성격", "이름": "이름", "맺음": "맺음", "종결": "종결"}


def analysis_table(analysis) -> str:
    out = [f"『{analysis.text}』"]
    out.append(f"  {'어절':<14}{'문장 성분':<9}형태소")
    out.append("  " + "─" * 62)
    for g in analysis.groups:
        surface = "".join(t.surface for t in g if t.surface) or g[0].form
        roles = {t.role for t in g if t.role is not Role.MARKER}
        role = next(iter(roles)).value if roles else "표지"
        out.append(f"  {surface:<14}{role:<8} "
                   + " ".join(f"{t.form}/{t.tag}" for t in g))
    return "\n".join(out)


def glyph_table(piece: Piece) -> str:
    out = [f"  {'낱말':<22}{'자리':<7}{'갈래':<6}{'성격':<16}화음"]
    out.append("  " + "─" * 76)
    for g, label in zip(piece.glyphs, piece.labels):
        if g.kind is Kind.CONCEPT:
            kind = "개념"
            spec = f"{g.tier}등급 {TIER_LABEL[g.tier]} · {g.quality.value}"
        elif g.kind is Kind.WORD:
            kind = f"{g.lang} 전용"
            spec = f"{g.tier}등급 {TIER_LABEL[g.tier]} · {g.quality.value}"
        else:
            kind = "글자"
            spec = "받아적기"
        out.append(f"  {label:<22}{g.role.value:<6}{kind:<6}{spec:<17}"
                   f"{len(g.events)}개")
    return "\n".join(out)


def score_table(piece: Piece) -> str:
    lo, hi = piece.ambitus
    out = [f"  화음 {len(piece.chords)}개 · 음역 {pitch.name(lo)}~{pitch.name(hi)}"
           f" · ♩={piece.tempo}",
           f"  {'때':>5} {'음':<20}{'자리':<7}{'길이':>4}  출처",
           "  " + "─" * 74]
    for n in sorted(piece.notes, key=lambda x: x.start):
        names = "+".join(pitch.name(p) for p in n.pitches)
        out.append(f"  {n.start:>5} {names:<20}{n.slot:<6}{n.duration:>4}"
                   f"  {n.source}")
    out.append("  (길이는 표현일 뿐 뜻을 담지 않는다)")
    return "\n".join(out)


def reading_table(r: Reading) -> str:
    out = [f"  {'되찾은 것':<26}{'자리':<7}{'갈래'}"]
    out.append("  " + "─" * 60)
    for it in r.items:
        if it.concept is not None:
            what = f"{it.concept.ko_form} ↔ {it.concept.en_form}"
            kind = "개념 (두 말 다)"
        elif it.kind is Kind.LETTER:
            what = it.form
            kind = f"글자 ({it.lang})"
        else:
            what = f"{it.form}/{it.tag}"
            kind = f"{it.lang} 전용"
        out.append(f"  {what:<26}{it.role.value:<6}{kind}")
    return "\n".join(out)


def rules_text() -> str:
    from ..core import codes as C
    from ..core.harmony import Quality

    L = []
    L.append("소리문 — 하나의 소리, 두 개의 말\n")
    L.append(f"■ 음역 — {pitch.name(pitch.LOWEST)} ~ {pitch.name(pitch.HIGHEST)}"
             f" (정확히 2옥타브)")
    L.append("  저음의 화음(2~3음)이 구조를, 고음의 홑음 멜로디가 낱말을 나른다.\n")

    L.append("■ 글리프 — 낱말 하나가 이렇게 적힌다")
    L.append("    [역할 화음] ([언어·받아적기 화음]) [이름 멜로디 3~10음] [맺음 화음]")
    L.append("  화음이면 구조, 홑음이면 이름 — 헷갈릴 길이 없다.\n")

    L.append("■ 이름 멜로디 — 익숙함과 감정을 멜로디가 직접 노래한다")
    L.append("  서명1  성질   기준음(G3) 위 장3도=장, 단3도=단, 삼전음=중성")
    L.append("  서명2  등급   서명1에서 뛰는 음정: "
             + " ".join(f"{t}등급 +{v}반음" for t, v in enumerate(C.TIER_LEAP)))
    L.append("  자릿음 번호   그 성질의 음계 위 계단 = 전단사 진법 한 자리")
    for q in Quality:
        L.append(f"    {q.value:<8} 음계 {C.SCALE[q]}  (진법 {C.base_of(q)})")
    L.append("")

    L.append("■ 문장 성분 — 저음 화음의 자리")
    for role in C.ROLE_PITCH:
        L.append(f"  {role.value:<7}{ENGLISH_NAME[role]:<13}"
                 f"근음 {pitch.name(C.ROLE_PITCH[role])}")
    L.append("")

    L.append("■ 하나의 말")
    L.append(f"  두 말에 다 있는 낱말은 '개념' 으로 적힌다. 개념 {len(Concepts.load()):,}개.")
    L.append("  조사·어미와 관사·어순은 소리에 담지 않고 읽어 낼 때 새로 짓는다.\n")

    L.append("■ 겹치지 않음")
    L.append("  되읽기가 (자리·대문자·갈래·말·등급·성질·번호·맺음)을 남김없이")
    L.append("  되찾는다. tools/verify.py 가 전수로 확인한다.")
    return "\n".join(L)


