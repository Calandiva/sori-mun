"""MusicXML 로 쓴다. MuseScore·Sibelius·Finale 에서 악보로 열린다."""

from __future__ import annotations

from pathlib import Path
from xml.sax.saxutils import escape

from ..compose import Score

DIVISIONS = 4           # 4분음표 = 4 등분  →  1등분 = 16분음표
BEATS_PER_MEASURE = 16  # 4/4 한 마디

_STEP = ["C", "C", "D", "D", "E", "F", "F", "G", "G", "A", "A", "B"]
_ALTER = [0, 1, 0, 1, 0, 0, 1, 0, 1, 0, 1, 0]

# 적을 수 있는 음가. (등분수, 이름, 점 개수)
_WRITABLE = [
    (16, "whole", 0), (12, "half", 1), (8, "half", 0), (6, "quarter", 1),
    (4, "quarter", 0), (3, "eighth", 1), (2, "eighth", 0), (1, "16th", 0),
]


def _split(dur: int) -> list[tuple[int, str, int]]:
    """임의의 길이를 적을 수 있는 음가들로 나눈다 (붙임줄로 이어 적는다)."""
    out = []
    left = dur
    while left > 0:
        for d, name, dots in _WRITABLE:
            if d <= left:
                out.append((d, name, dots))
                left -= d
                break
        else:  # pragma: no cover
            break
    return out


def _pitch_xml(midi: int) -> str:
    pc, octave = midi % 12, midi // 12 - 1
    alter = f"<alter>{_ALTER[pc]}</alter>" if _ALTER[pc] else ""
    return f"<pitch><step>{_STEP[pc]}</step>{alter}<octave>{octave}</octave></pitch>"


def _events(score: Score) -> list[tuple[int, int, tuple[int, ...] | None, str]]:
    """(시작, 길이, 음높이들 또는 None=쉼표, 설명) 을 시간 순으로."""
    notes = sorted(score.notes, key=lambda n: (n.start, min(n.pitches)))
    out = []
    cursor = 0
    for n in notes:
        if n.start > cursor:
            out.append((cursor, n.start - cursor, None, ""))
        if n.start < cursor:
            continue  # 겹치는 소리는 앞의 것을 살린다
        out.append((n.start, n.duration, n.pitches, f"{n.source} {n.role}"))
        cursor = n.end
    return out


def write(score: Score, path: Path | str, title: str | None = None) -> Path:
    path = Path(path)
    title = title or (score.sentence.text if score.sentence else "소리문")

    body: list[str] = []
    measure = 1
    filled = 0
    first = True

    def open_measure() -> None:
        nonlocal first
        body.append(f'<measure number="{measure}">')
        if first:
            body.append(
                f"<attributes><divisions>{DIVISIONS}</divisions>"
                "<key><fifths>0</fifths></key>"
                "<time><beats>4</beats><beat-type>4</beat-type></time>"
                "<clef><sign>G</sign><line>2</line></clef>"
                "<staff-details><staff-lines>5</staff-lines></staff-details>"
                "</attributes>"
            )
            body.append(
                f"<direction placement=\"above\"><direction-type>"
                f"<metronome><beat-unit>quarter</beat-unit>"
                f"<per-minute>{score.tempo}</per-minute></metronome>"
                f"</direction-type><sound tempo=\"{score.tempo}\"/></direction>"
            )
            first = False

    open_measure()

    for _start, dur, pitches, label in _events(score):
        left = dur
        while left > 0:
            take = min(left, BEATS_PER_MEASURE - filled)
            parts = _split(take)
            for i, (d, name, dots) in enumerate(parts):
                # 마디를 넘거나 여러 음가로 쪼개졌으면 붙임줄로 잇는다.
                more_after = (left - take > 0) or (i < len(parts) - 1)
                came_from = (left != dur) or (i > 0)
                if pitches is None:
                    body.append(
                        f"<note><rest/><duration>{d}</duration>"
                        f"<type>{name}</type>{'<dot/>' * dots}</note>"
                    )
                else:
                    for j, p in enumerate(pitches):
                        ties = ""
                        tied = ""
                        if came_from:
                            ties += '<tie type="stop"/>'
                            tied += '<tied type="stop"/>'
                        if more_after:
                            ties += '<tie type="start"/>'
                            tied += '<tied type="start"/>'
                        notations = f"<notations>{tied}</notations>" if tied else ""
                        lyric = ""
                        if j == 0 and label and not came_from:
                            lyric = (f"<lyric><text>{escape(label.split()[0])}"
                                     f"</text></lyric>")
                        body.append(
                            f"<note>{'<chord/>' if j else ''}{_pitch_xml(p)}"
                            f"<duration>{d}</duration>{ties}"
                            f"<type>{name}</type>{'<dot/>' * dots}"
                            f"{notations}{lyric}</note>"
                        )
                filled += d
            left -= take
            if filled >= BEATS_PER_MEASURE:
                body.append("</measure>")
                measure += 1
                filled = 0
                open_measure()

    if filled < BEATS_PER_MEASURE and filled > 0:
        rest = BEATS_PER_MEASURE - filled
        for d, name, dots in _split(rest):
            body.append(
                f"<note><rest/><duration>{d}</duration>"
                f"<type>{name}</type>{'<dot/>' * dots}</note>"
            )
    body.append("</measure>")

    xml = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<!DOCTYPE score-partwise PUBLIC "-//Recordare//DTD MusicXML 3.1 Partwise//EN"'
        ' "http://www.musicxml.org/dtds/partwise.dtd">\n'
        '<score-partwise version="3.1">'
        f"<work><work-title>{escape(title)}</work-title></work>"
        "<identification><encoding><software>sori-mun</software></encoding>"
        "</identification>"
        '<part-list><score-part id="P1">'
        "<part-name>소리문</part-name></score-part></part-list>"
        '<part id="P1">' + "".join(body) + "</part></score-partwise>\n"
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(xml, encoding="utf-8")
    return path
