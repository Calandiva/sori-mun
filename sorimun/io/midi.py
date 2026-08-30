"""표준 MIDI 파일 쓰기. 바깥 라이브러리를 쓰지 않는다."""

from __future__ import annotations

import struct
from pathlib import Path

from ..compose import Score

TICKS_PER_QUARTER = 480
TICKS_PER_UNIT = TICKS_PER_QUARTER // 4   # 1단위 = 16분음표


def _varlen(n: int) -> bytes:
    """MIDI 가변길이 수."""
    if n < 0:
        raise ValueError("음수 델타")
    out = bytearray([n & 0x7F])
    n >>= 7
    while n:
        out.append((n & 0x7F) | 0x80)
        n >>= 7
    return bytes(reversed(out))


def _meta(kind: int, payload: bytes) -> bytes:
    return b"\xff" + bytes([kind]) + _varlen(len(payload)) + payload


def _track(events: list[tuple[int, int, bytes]]) -> bytes:
    """(절대틱, 우선순위, 바이트) 목록을 트랙 덩어리로."""
    events.sort(key=lambda e: (e[0], e[1]))
    out = bytearray()
    prev = 0
    for tick, _prio, data in events:
        out += _varlen(tick - prev) + data
        prev = tick
    out += _varlen(0) + _meta(0x2F, b"")   # 트랙 끝
    return b"MTrk" + struct.pack(">I", len(out)) + bytes(out)


def write(score: Score, path: Path | str, channel: int = 0,
          program: int = 0, title: str | None = None) -> Path:
    """악보를 .mid 파일로 쓴다.

    program 은 GM 음색 번호. 0 = 어쿠스틱 그랜드 피아노.
    """
    path = Path(path)
    events: list[tuple[int, int, bytes]] = []

    name = (title or (score.sentence.text if score.sentence else "소리문"))[:120]
    events.append((0, 0, _meta(0x03, name.encode("utf-8"))))
    mpqn = int(60_000_000 / max(1, score.tempo))
    events.append((0, 0, _meta(0x51, struct.pack(">I", mpqn)[1:])))
    events.append((0, 0, bytes([0xC0 | channel, program])))

    for n in score.notes:
        on = n.start * TICKS_PER_UNIT
        off = on + max(1, n.duration * TICKS_PER_UNIT)
        for p in n.pitches:
            # 음 끄기를 먼저 처리해야 같은 음이 겹칠 때 끊기지 않는다.
            events.append((off, 0, bytes([0x80 | channel, p, 0])))
            events.append((on, 1, bytes([0x90 | channel, p, n.velocity])))

    header = b"MThd" + struct.pack(">IHHH", 6, 0, 1, TICKS_PER_QUARTER)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(header + _track(events))
    return path
