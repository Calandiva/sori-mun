"""받아적기 — 사전에 없는 낱말을 글자로 옮긴다.

낱말이 사전에 없어도 소리에서 글로 온전히 돌아와야 한다. 그래서 그런
낱말은 글자 하나하나에 번호를 매겨 받아 적는다.

    한국어  한글 음절 11,172자 + 자모 + 아스키
    영어    아스키

한 글자가 글리프 하나가 되므로 사전에 없는 낱말은 길고 더듬거리게
울린다 — 낯선 말을 낯설게 옮기는 셈이다.
"""

from __future__ import annotations

_ASCII = [chr(c) for c in range(0x20, 0x7F)]
_HANGUL = [chr(c) for c in range(0xAC00, 0xD7A4)]          # 가 ~ 힣
_JAMO = [chr(c) for c in range(0x3131, 0x3164)]            # ㄱ ~ ㅣ

ALPHABET: dict[str, list[str]] = {
    "ko": _ASCII + _JAMO + _HANGUL,
    "en": _ASCII,
}
_INDEX: dict[str, dict[str, int]] = {
    lang: {ch: i for i, ch in enumerate(chars)} for lang, chars in ALPHABET.items()
}


def size(lang: str) -> int:
    return len(ALPHABET[lang])


def to_index(lang: str, ch: str) -> int | None:
    """글자를 번호로. 그 언어의 글자표에 없으면 None."""
    return _INDEX[lang].get(ch)


def to_char(lang: str, index: int) -> str:
    chars = ALPHABET[lang]
    if not 0 <= index < len(chars):
        raise ValueError(f"글자 번호 {index} 는 {lang} 글자표 밖이다")
    return chars[index]


def spellable(lang: str, word: str) -> bool:
    return all(to_index(lang, ch) is not None for ch in word)
