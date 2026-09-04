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
    L.append("  모든 소리의 꼭대기가 멜로디다. 멜로디만 들으면 낱말이고,")
    L.append("  함께 우는 화성을 들으면 그 낱말의 역할이다.\n")

    L.append("■ 글리프 — 낱말 하나가 이렇게 적힌다")
    L.append("    [첫 자릿음+베이스 C3+역할 내성] [자릿음 …] [종지1(+표지 내성)] [종지2]")
    L.append("  베이스 C3 이 울리면 새 낱말 — 경계 표시가 따로 없다.\n")

    L.append("■ 이름 멜로디 — 익숙함과 감정을 멜로디가 직접 노래한다")
    for q in Quality:
        ts = C.TONIC_SET[q]
        L.append(f"  {q.value:<7} 조 " 
                 + " ".join(pitch.name(t) for t in ts)
                 + f" — (번호+3×등급) 나머지 {len(ts)}")
    L.append("  종지1  성질·조  으뜸음 위 장3도=장, 단3도=단, 삼전음=중성")
    L.append("                 여덟 닻(" 
             + " ".join(pitch.name(s2) for s2 in sorted(C.SIG_ANCHOR))
             + ")이 서로소라 홀로 풀린다")
    L.append("  종지2  등급   종지1에서 아래로 해결: "
             + " ".join(f"{t}등급 −{v}반음" for t, v in enumerate(C.TIER_LEAP)))
    L.append("  자릿음 번호   으뜸음 위 그 성질의 음계 계단 = 전단사 진법 한 자리")
    for q in Quality:
        L.append(f"    {q.value:<8} 음계 {C.SCALE[q]}  (진법 {C.base_of(q)})")
    L.append("")

    L.append("■ 문장 성분 — 베이스 C3 위 역할 내성")
    for role, iv in C.ROLE_INNER.items():
        L.append(f"  {role.value:<7}{ENGLISH_NAME[role]:<13}"
                 f"내성 +{iv} ({pitch.name(C.PEDAL + iv)})")
    L.append("")
    L.append("■ 표지 내성 — 종지1 아래 (없으면 개념)")
    for (kind, lg), m in C.KIND_MARK.items():
        nm = "전용" if kind == "WORD" else "글자"
        L.append(f"  {lg} {nm:<4} {pitch.name(m)}")
    L.append(f"  대문자   {pitch.name(C.FLAG_MARK)}")
    L.append(f"  이음     {pitch.name(C.JOIN_MARK)}")
    L.append("")

    L.append("■ 하나의 말")
    L.append(f"  두 말에 다 있는 낱말은 '개념' 으로 적힌다. 개념 {len(Concepts.load()):,}개.")
    L.append("  조사·어미와 관사·어순은 소리에 담지 않고 읽어 낼 때 새로 짓는다.\n")

    L.append("■ 겹치지 않음")
    L.append("  되읽기가 (자리·대문자·이음·갈래·말·등급·성질·번호)를 남김없이")
    L.append("  되찾는다. tools/verify.py 가 전수로 확인한다.")
    return "\n".join(L)


