"""분석·사전·입출력."""

import xml.etree.ElementTree as ET

import pytest

from sorimun.compose import Composer
from sorimun.core.roles import Role
from sorimun.decompose import read, render
from sorimun.dictionary import Dictionary
from sorimun.io import midi, midi_read, musicxml, wave_out


@pytest.mark.parametrize("text,want", [
    ("물이 얼음이 되었다.", [Role.SUBJECT, Role.COMPLEMENT, Role.PREDICATE]),
    ("아름다운 노래가 밤을 어루만졌다.",
     [Role.ADNOMINAL, Role.SUBJECT, Role.OBJECT, Role.PREDICATE]),
])
def test_한국어_성분(ko, text, want):
    got = [t.role for t in ko.analyze(text).tokens if t.role is not Role.MARKER]
    assert got == want


@pytest.mark.parametrize("text,want", [
    ("The child laughed quietly.",
     [Role.SUBJECT, Role.PREDICATE, Role.ADVERBIAL]),
    ("She sings sad songs.",
     [Role.SUBJECT, Role.PREDICATE, Role.ADNOMINAL, Role.OBJECT]),
])
def test_영어_성분(en, text, want):
    got = [t.role for t in en.analyze(text).tokens if t.role is not Role.MARKER]
    assert got == want


def test_영어_굴절_분해(en):
    forms = [(t.form, t.tag) for t in en.analyze("She sings sad songs.").tokens]
    assert ("sing", "VB") in forms and ("«3sg»", "GRAM") in forms
    assert ("song", "NN") in forms and ("«plural»", "GRAM") in forms


@pytest.mark.parametrize("lang", ["ko", "en"])
def test_사전_양방향(lang):
    d = Dictionary.load(lang)
    for e in list(d.entries)[::500]:
        assert d.at(e.tier, e.quality, e.index) is e


def test_midi_왕복(en, tmp_path):
    p = Composer("en", analyzer=en).compose(
        en.analyze("The child laughed quietly."))
    f = midi.write(p, tmp_path / "a.mid")
    assert midi_read.chords(f) == p.chords
    assert render(read(midi_read.chords(f)), "en", en) == \
        "The child laughed quietly."


def test_음이름으로_직접_넣기(en):
    p = Composer("en", analyzer=en).compose(en.analyze("Love is strong."))
    from sorimun.core import pitch
    text = " ".join("+".join(pitch.name(x) for x in c) for c in p.chords)
    assert midi_read.parse_notes(text) == p.chords


def test_wav(en, tmp_path):
    import wave as W
    p = Composer("en", analyzer=en).compose(en.analyze("Love is strong."))
    f = wave_out.write(p, tmp_path / "a.wav")
    with W.open(str(f)) as w:
        assert w.getframerate() == 44100 and w.getnframes() > 1000


def test_musicxml(en, tmp_path):
    p = Composer("en", analyzer=en).compose(en.analyze("Love is strong."))
    f = musicxml.write(p, tmp_path / "a.musicxml")
    root = ET.parse(f).getroot()
    for m in root.findall(".//measure"):
        total = sum(int(d.text) for n in m.findall("note")
                    if n.find("chord") is None for d in n.findall("duration"))
        assert total == 16


def test_cli(tmp_path, capsys):
    from sorimun.cli import main
    assert main(["옮김", "The child laughed quietly.", "-o", str(tmp_path),
                 "-n", "t", "--mid", "-q"]) == 0
    assert main(["읽기", "-f", str(tmp_path / "t.mid"), "-q"]) == 0
    out = capsys.readouterr().out
    assert "아이가 조용히 웃었다." in out
    assert "The child laughed quietly." in out
