"""터미널에 보여 주는 표."""

from __future__ import annotations

from ..compose import Piece
from ..concepts import Concepts
from ..core import codes as C, pitch
from ..core.glyph import Kind
from ..core.roles import ENGLISH_NAME, Role
from ..decompose import Reading
from ..dictionary import TIER_LABEL

SLOT_MARK = {"역할": "자리", "의미": "성격", "언어": "말", "받아적기": "받아적기",
             "자리": "이름", "맺음": "맺음", "종결": "종결"}


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
    from ..core.banks import BANKS
    from ..core.harmony import Quality

    L = []
    L.append("소리문 — 하나의 소리, 두 개의 말\n")
    L.append(f"■ 음역 — {pitch.name(pitch.LOWEST)} ~ {pitch.name(pitch.HIGHEST)}"
             f" (정확히 2옥타브)")
    L.append("  모든 화음은 2음 또는 3음이다.\n")

    L.append("■ 글리프 — 낱말 하나가 이렇게 적힌다")
    L.append("    [역할 화음] [머리 화음] [자릿 화음 × k] [맺음 화음]")
    L.append("  역할 화음   문장 성분. 모양이 자리를, 근음이 음역대를 말한다.")
    L.append("  머리 화음   개념(두 말 공통) / 언어 전용 / 글자 받아적기")
    L.append("  자릿 화음   번호. 근음 어긋남 × 화음 모양 으로 한 자리.")
    L.append("  맺음 화음   글리프 끝. 어절이 이어지는지 끊기는지도 말한다.\n")

    L.append("■ 부호를 나르는 것은 음높이와 화성뿐이다")
    L.append("  음가와 쉼표는 표현일 뿐 뜻을 담지 않는다. 연주하는 사람이")
    L.append("  길이를 흔들어도 뜻은 그대로다.\n")

    L.append("■ 두 축")
    L.append(f"  협화도 ← 빈도   흔할수록 순한 화음 (등급 0~5)")
    L.append(f"  장·단  ← 감정   긍정은 장, 부정은 단, 나머지는 중성")
    L.append(f"  {'등급':<6}{'뜻':<14}{'장':<12}{'단':<12}중성")
    for t in range(6):
        row = "  ".join(f"{BANKS.meaning[(t,q)].voicing}" for q in Quality)
        L.append(f"  {t:<6}{TIER_LABEL[t]:<13}{row}")
    L.append("")

    L.append("■ 문장 성분 — 여덟 자리를 두 말이 함께 쓴다")
    L.append(f"  {'자리':<7}{'english':<13}{'역할 화음 근음':<15}{'자릿 음역대'}")
    for role in C.ROLE_PITCH:
        L.append(f"  {role.value:<7}{ENGLISH_NAME[role]:<13}"
                 f"{pitch.name(C.ROLE_PITCH[role]):<15}"
                 f"{pitch.name(C.BAND[role])}부터")
    L.append("")

    L.append("■ 하나의 말")
    L.append("  두 말에 다 있는 낱말은 '개념' 으로 적힌다. 소리에는 개념 번호만")
    L.append("  들어가고 어느 말인지는 들어가지 않는다. 그래서 영어로 적은")
    L.append(f"  소리를 한국어로 읽어 낼 수 있다. 개념 {len(Concepts.load()):,}개.")
    L.append("  조사·어미와 관사·전치사는 그 말의 것이므로 소리에 담지 않고,")
    L.append("  읽어 낼 때 자리(문장 성분)를 보고 새로 붙인다.\n")

    L.append("■ 겹치지 않음")
    L.append("  되읽기가 (자리·갈래·말·등급·성질·번호·맺음)을 남김없이 되찾는다.")
    L.append("  되찾기가 적기의 왼쪽 역이므로, 서로 다른 낱말이 같은 소리를")
    L.append("  가질 수 없다. tools/verify.py 가 전수로 확인한다.")
    return "\n".join(L)
