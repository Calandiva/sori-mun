"""MIDI 파일에서 화음의 차례를 읽는다 — 소리를 다시 넣는 길.

되읽기는 음높이와 화성만 본다. 그러므로 이 자리에서 필요한 것은
'어떤 음들이 함께, 어떤 차례로 울렸는가' 뿐이다. 길이는 읽되 쓰지
않는다. 사람이 연주해 길이가 흔들려도 뜻은 그대로다.

같은 때에 시작한 음들을 한 화음으로 묶는다. 조금 어긋나 눌린 것도
`slack` 안이면 한 화음으로 본다.
"""

from __future__ import annotations

import struct
from pathlib import Path


def _read_varlen(data: bytes, i: int) -> tuple[int, int]:
    n = 0
    while True:
        b = data[i]
        i += 1
        n = (n << 7) | (b & 0x7F)
        if not b & 0x80:
            return n, i


def note_events(path: Path | str) -> list[tuple[int, int]]:
    """(시작 틱, 음높이) 목록을 시간 순으로."""
    data = Path(path).read_bytes()
    if data[:4] != b"MThd":
        raise ValueError("MIDI 파일이 아니다")
    _len, _fmt, ntrk, div = struct.unpack(">IHHH", data[4:14])
    i = 14
    out: list[tuple[int, int]] = []

    for _ in range(ntrk):
        if data[i:i + 4] != b"MTrk":
            break
        size = struct.unpack(">I", data[i + 4:i + 8])[0]
        end = i + 8 + size
        j = i + 8
        tick = 0
        status = 0
        while j < end:
            delta, j = _read_varlen(data, j)
            tick += delta
            b = data[j]
            if b & 0x80:
                status = b
                j += 1
            if status == 0xFF:
                kind = data[j]
                j += 1
                ln, j = _read_varlen(data, j)
                j += ln
                if kind == 0x2F:
                    break
            elif status in (0xF0, 0xF7):
                ln, j = _read_varlen(data, j)
                j += ln
            else:
                hi = status & 0xF0
                if hi in (0x90, 0x80, 0xA0, 0xB0, 0xE0):
                    a, b2 = data[j], data[j + 1]
                    j += 2
                    if hi == 0x90 and b2 > 0:
                        out.append((tick, a))
                elif hi in (0xC0, 0xD0):
                    j += 1
                else:
                    j += 1
        i = end

    out.sort()
    return out


def chords(path: Path | str, slack: int = 8) -> list[tuple[int, ...]]:
    """MIDI 파일을 화음의 차례로. 되읽기에 그대로 넣을 수 있다."""
    out: list[tuple[int, ...]] = []
    cur: list[int] = []
    at = None
    for tick, note in note_events(path):
        if at is None or tick - at > slack:
            if cur:
                out.append(tuple(sorted(cur)))
            cur, at = [note], tick
        else:
            cur.append(note)
    if cur:
        out.append(tuple(sorted(cur)))
    return out


def parse_notes(text: str) -> list[tuple[int, ...]]:
    """손으로 적은 음이름을 화음의 차례로.

        "C3+E3+E4  G3+A3+F4  ..."  또는  "48+52+64 55+57+65"
    """
    names = ["C", "C#", "D", "D#", "E", "F", "F#", "G", "G#", "A", "A#", "B"]
    alias = {"DB": "C#", "EB": "D#", "GB": "F#", "AB": "G#", "BB": "A#"}
    out = []
    for token in text.replace(",", " ").split():
        ps = []
        for part in token.split("+"):
            part = part.strip()
            if not part:
                continue
            if part.isdigit():
                ps.append(int(part))
                continue
            body, octave = part[:-1].upper(), part[-1]
            body = alias.get(body, body)
            if body not in names or not octave.isdigit():
                raise ValueError(f"음이름을 알 수 없다: {part}")
            ps.append(names.index(body) + (int(octave) + 1) * 12)
        if ps:
            out.append(tuple(sorted(ps)))
    return out
