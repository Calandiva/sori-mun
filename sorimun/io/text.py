"""터미널에 보여 주는 악보와 분석표."""

from __future__ import annotations

from ..compose import ROLE_RULES, Score
from ..core import pitch
from ..core.analyze import Sentence
from ..core.markers import GESTURE, GESTURE_NAME
from ..core.tags import KOREAN_NAME, Role
from ..dictionary import Dictionary

TIER_LABEL = ("아주 흔함", "흔함", "보통", "드묾", "아주 드묾", "희귀·미등재")
QUALITY_KO = {"major": "장(긍정)", "minor": "단(부정)", "neutral": "중성"}


def analysis_table(sentence: Sentence) -> str:
    """문장 성분 분석표."""
    out = [f"『{sentence.text}』"]
    out.append(f"  {'어절':<12}{'성분':<7}{'형태소'}")
    out.append("  " + "─" * 62)
    for e in sentence.eojeols:
        ms = " ".join(f"{m.form}/{m.tag}" for m in e.morphs)
        mark = "~" if e.guessed else " "
        out.append(f"  {e.surface:<12}{e.role.value:<6}{mark} {ms}")
    if any(e.guessed for e in sentence.eojeols):
        out.append("  (~ 는 조사가 없어 자리로 어림한 것)")
    return "\n".join(out)


def mapping_table(score: Score, dictionary: Dictionary) -> str:
    """낱말이 어떤 규칙으로 어떤 소리가 되었는지."""
    out = [f"  {'형태소':<12}{'품사':<12}{'등급':<12}{'성질':<10}{'음형'}"]
    out.append("  " + "─" * 72)
    seen = set()
    for label, entry, role in score.entries:
        if label in seen:
            continue
        seen.add(label)
        name = KOREAN_NAME.get(entry.tag, entry.tag)
        if entry.is_marker:
            g = GESTURE[entry.tag]
            tier = f"표지 {g:+d}반음"
            qual = GESTURE_NAME[entry.tag]
        else:
            tier = f"{entry.tier} {TIER_LABEL[entry.tier]}"
            if not entry.known:
                tier = "미등재"
            qual = QUALITY_KO.get(entry.quality, entry.quality)
            if entry.polarity:
                qual += f" {entry.polarity:+d}"
        out.append(
            f"  {entry.form + '/' + entry.tag:<12}{name:<11}{tier:<13}"
            f"{qual:<11}{entry.phrase.n_events}음형"
        )
    return "\n".join(out)


def score_table(score: Score) -> str:
    """실제로 울리는 소리를 시간 순으로."""
    lo, hi = score.ambitus
    out = [
        f"  길이 {score.length}단위 ({score.length / 4:.1f}박, "
        f"♩={score.tempo})   음역 {pitch.name(lo)}~{pitch.name(hi)}"
    ]
    out.append(f"  {'때':>5} {'음':<20}{'길이':>5}{'세기':>5}  {'성분':<7}{'출처'}")
    out.append("  " + "─" * 72)
    cursor = 0
    for n in sorted(score.notes, key=lambda x: x.start):
        if n.start > cursor:
            out.append(f"  {cursor:>5} {'·쉼표·':<20}{n.start - cursor:>5}")
        ko = "+".join(pitch.name_ko(p) for p in n.pitches)
        out.append(
            f"  {n.start:>5} {n.names:<20}{n.duration:>5}{n.velocity:>5}"
            f"  {n.role:<7}{n.source}   {ko}"
        )
        cursor = max(cursor, n.end)
    return "\n".join(out)


def role_legend() -> str:
    """문장 성분이 소리에 거는 조건표."""
    out = [f"  {'성분':<7}{'목표 최저음':<13}{'음가':<8}{'세기':<6}{'성격'}"]
    out.append("  " + "─" * 74)
    for role in (Role.INDEPENDENT, Role.ADNOMINAL, Role.OBJECT, Role.COMPLEMENT,
                 Role.SUBJECT, Role.ADVERBIAL, Role.PREDICATE):
        r = ROLE_RULES[role]
        ratio = (f"×{r.dur_num}" if r.dur_den == 1
                 else f"×{r.dur_num}/{r.dur_den}")
        out.append(
            f"  {role.value:<7}{pitch.name(r.register)} ({r.register:>2})   "
            f"{ratio:<8}{r.velocity:<6}{r.note}"
        )
    return "\n".join(out)


def entry_card(entry, dictionary: Dictionary | None = None) -> str:
    """사전 항목 한 장."""
    ph = entry.phrase
    name = KOREAN_NAME.get(entry.tag, entry.tag)
    lines = [f"  {entry.form} / {entry.tag}  ({name})"]
    if entry.is_marker:
        lines.append(
            f"    갈래   문법 표지 — {GESTURE_NAME[entry.tag]} "
            f"({GESTURE[entry.tag]:+d}반음)"
        )
    else:
        tier = "미등재 (규칙으로 즉석 생성)" if not entry.known else \
            f"{entry.tier}등급 · {TIER_LABEL[entry.tier]}"
        lines.append(f"    빈도   {entry.freq:,}  (순위 {entry.rank:,})")
        lines.append(f"    협화도 {tier}")
        lines.append(
            f"    성질   {QUALITY_KO.get(entry.quality, entry.quality)}"
            + (f"  (극성 {entry.polarity:+d})" if entry.polarity else "")
        )
    bottom = pitch.place(60, ph.ambitus)
    rendered = ph.render(bottom)
    lines.append(f"    음형   {ph.n_events}개 화음 · 폭 {ph.ambitus}반음 · 길이 {ph.length}단위")
    for i, (ps, dur, rest) in enumerate(rendered, 1):
        names = "+".join(pitch.name(p) for p in ps)
        ko = "+".join(pitch.name_ko(p) for p in ps)
        tail = f"  뒤쉼 {rest}" if rest else ""
        lines.append(f"      {i}. {names:<18}{ko:<18}길이 {dur}{tail}")
    lines.append(f"    코드   {entry.code}")
    return "\n".join(lines)
