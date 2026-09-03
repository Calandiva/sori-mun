"""영어 굴절 — 붙이고 떼기.

한국어는 '어루만지 + 었 + 다' 처럼 형태소가 따로 서지만, 영어는
'touched' 처럼 낱말 안에 녹아 있다. 소리는 둘을 같은 개념으로 담아야
하므로, 영어 쪽도 밑말과 굴절로 갈라 놓는다.

    touched  →  touch + «past»
    songs    →  song  + «plural»
    singing  →  sing  + «ing»

되읽을 때는 거꾸로 붙인다. 붙인 것이 원문과 다르면 그 낱말은 개념이
아니라 낱말 그대로 적는다 — 그래야 원문이 반드시 돌아온다.
"""

from __future__ import annotations

PAST = "«past»"
THIRD = "«3sg»"
PLURAL = "«plural»"
ING = "«ing»"
NOT = "«not»"
WILL = "«will»"
GRAMS = (PAST, THIRD, PLURAL, ING, NOT, WILL)
TAG = "GRAM"

# 자주 쓰는 불규칙 동사. 여기 없는 것은 규칙으로 붙였다 떼었다 한다.
IRREGULAR_PAST = {
    "be": "was", "become": "became", "begin": "began", "break": "broke",
    "bring": "brought", "build": "built", "buy": "bought", "catch": "caught",
    "choose": "chose", "come": "came", "do": "did", "draw": "drew",
    "drink": "drank", "drive": "drove", "eat": "ate", "fall": "fell",
    "feel": "felt", "find": "found", "fly": "flew", "forget": "forgot",
    "get": "got", "give": "gave", "go": "went", "grow": "grew",
    "have": "had", "hear": "heard", "hold": "held", "keep": "kept",
    "know": "knew", "leave": "left", "lose": "lost", "make": "made",
    "meet": "met", "pay": "paid", "put": "put", "read": "read",
    "run": "ran", "say": "said", "see": "saw", "sell": "sold",
    "send": "sent", "sing": "sang", "sit": "sat", "sleep": "slept",
    "speak": "spoke", "stand": "stood", "take": "took", "teach": "taught",
    "tell": "told", "think": "thought", "understand": "understood",
    "wear": "wore", "win": "won", "write": "wrote",
    "shake": "shook", "throw": "threw", "blow": "blew", "ring": "rang",
    "swim": "swam", "rise": "rose", "shine": "shone", "hide": "hid",
    "lie": "lay", "lay": "laid", "seek": "sought", "spend": "spent",
    "lend": "lent", "bend": "bent", "feed": "fed", "lead": "led",
    "permit": "permitted", "admit": "admitted", "submit": "submitted",
    "commit": "committed", "omit": "omitted", "regret": "regretted",
    "upset": "upset",
    "hurt": "hurt", "cost": "cost", "cut": "cut", "let": "let",
    "set": "set", "shut": "shut", "hit": "hit", "quit": "quit",
}
_PAST_TO_BASE = {v: k for k, v in IRREGULAR_PAST.items()}

IRREGULAR_PLURAL = {
    "child": "children", "man": "men", "woman": "women", "person": "people",
    "foot": "feet", "tooth": "teeth", "mouse": "mice", "goose": "geese",
    "life": "lives", "leaf": "leaves", "knife": "knives", "wife": "wives",
}
_PLURAL_TO_BASE = {v: k for k, v in IRREGULAR_PLURAL.items()}

_VOWELS = "aeiou"


_NO_DOUBLE = ("er", "en", "on", "el", "ow", "it", "et", "om", "an")


def _double(stem: str) -> bool:
    if len(stem) >= 5 and stem.endswith(_NO_DOUBLE):
        return False        # 무강세 어미 어림 — cover, happen, visit …
    return (len(stem) >= 3 and stem[-1] not in _VOWELS + "wxy"
            and stem[-2] in _VOWELS and stem[-3] not in _VOWELS)


def _add_s(w: str) -> str:
    if w.endswith(("s", "x", "z", "ch", "sh")):
        return w + "es"
    if w.endswith("y") and len(w) > 1 and w[-2] not in _VOWELS:
        return w[:-1] + "ies"
    if w.endswith("o") and len(w) > 1 and w[-2] not in _VOWELS:
        return w + "es"
    return w + "s"


def apply(word: str, gram: str) -> str:
    """밑말에 굴절을 붙인다. 첫 대문자는 지키고 표는 소문자로 찾는다."""
    if word[:1].isupper():
        low = apply(word[0].lower() + word[1:], gram)
        return low[:1].upper() + low[1:]
    if gram == PAST:
        if word in IRREGULAR_PAST:
            return IRREGULAR_PAST[word]
        if word.endswith("e"):
            return word + "d"
        if word.endswith("y") and len(word) > 1 and word[-2] not in _VOWELS:
            return word[:-1] + "ied"
        if _double(word):
            return word + word[-1] + "ed"
        return word + "ed"
    if gram in (THIRD, PLURAL):
        if gram == PLURAL and word in IRREGULAR_PLURAL:
            return IRREGULAR_PLURAL[word]
        if gram == THIRD and word == "be":
            return "is"
        if gram == THIRD and word == "have":
            return "has"
        if gram == THIRD and word == "do":
            return "does"
        return _add_s(word)
    if gram == ING:
        if word.endswith("ie"):
            return word[:-2] + "ying"
        if word.endswith("e") and not word.endswith("ee"):
            return word[:-1] + "ing"
        if _double(word):
            return word + word[-1] + "ing"
        return word + "ing"
    return word


def split(word: str, tag: str, known) -> tuple[str, str] | None:
    """굴절형을 (밑말, 굴절) 로 가른다. 가를 수 없으면 None.

    known(form, tag) 이 그 꼴이 사전에 있는지 답한다.
    """
    from . import tags_en as E

    if tag == E.VB:
        if word in _PAST_TO_BASE and known(_PAST_TO_BASE[word], E.VB):
            return _PAST_TO_BASE[word], PAST
        for base, gram in _candidates_vb(word):
            if known(base, E.VB) and apply(base, gram) == word:
                return base, gram
    elif tag == E.NN:
        if word in _PLURAL_TO_BASE and known(_PLURAL_TO_BASE[word], E.NN):
            return _PLURAL_TO_BASE[word], PLURAL
        for base in _candidates_nn(word):
            if known(base, E.NN) and apply(base, PLURAL) == word:
                return base, PLURAL
    return None


def _candidates_vb(w: str):
    if w.endswith("ied") and len(w) > 4:
        yield w[:-3] + "y", PAST
    if w.endswith("ed") and len(w) > 3:
        yield w[:-2], PAST
        yield w[:-1], PAST
        if len(w) > 4 and w[-3] == w[-4]:
            yield w[:-3], PAST
    if w.endswith("ing") and len(w) > 4:
        yield w[:-3], ING
        yield w[:-3] + "e", ING
        if len(w) > 5 and w[-4] == w[-5]:
            yield w[:-4], ING
    if w.endswith("ies") and len(w) > 4:
        yield w[:-3] + "y", THIRD
    if w.endswith("es") and len(w) > 3:
        yield w[:-2], THIRD
    if w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        yield w[:-1], THIRD


def _candidates_nn(w: str):
    if w.endswith("ies") and len(w) > 4:
        yield w[:-3] + "y"
    if w.endswith("es") and len(w) > 3:
        yield w[:-2]
    if w.endswith("s") and not w.endswith("ss") and len(w) > 2:
        yield w[:-1]
