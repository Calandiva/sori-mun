"""처음부터 끝까지."""

import xml.etree.ElementTree as ET

import pytest

from sorimun.io import midi, musicxml, wave_out

TEXT = "아름다운 노래가 어두운 밤을 천천히 어루만졌다."


@pytest.fixture(scope="module")
def score(analyzer, composer):
    return composer.compose(analyzer.analyze(TEXT))


def test_midi(score, tmp_path):
    p = midi.write(score, tmp_path / "a.mid")
    data = p.read_bytes()
    assert data.startswith(b"MThd")
    assert b"MTrk" in data
    assert data.endswith(b"\xff\x2f\x00")


def test_wav(score, tmp_path):
    p = wave_out.write(score, tmp_path / "a.wav")
    import wave as W
    with W.open(str(p)) as w:
        assert w.getnchannels() == 1
        assert w.getframerate() == 44100
        assert w.getnframes() > 44100      # 1초는 넘는다


def test_musicxml_마디가_맞는다(score, tmp_path):
    p = musicxml.write(score, tmp_path / "a.musicxml")
    root = ET.parse(p).getroot()
    measures = root.findall(".//measure")
    assert measures
    for m in measures:
        total = sum(
            int(d.text)
            for n in m.findall("note")
            if n.find("chord") is None
            for d in n.findall("duration")
        )
        assert total == 16, f"마디 {m.get('number')} 등분합 {total}"


def test_cli_사전(capsys):
    from sorimun.cli import main
    assert main(["사전", "은"]) == 0
    out = capsys.readouterr().out
    assert "보조사" in out and "하행 완전5도" in out


def test_cli_규칙(capsys):
    from sorimun.cli import main
    assert main(["규칙"]) == 0
    out = capsys.readouterr().out
    assert "C3 ~ C5" in out and "겹치지 않음" in out


def test_cli_옮김(tmp_path, capsys):
    from sorimun.cli import main
    rc = main(["옮김", TEXT, "-o", str(tmp_path), "--mid", "--xml", "-q"])
    assert rc == 0
    assert (tmp_path / "소리문.mid").exists()
    assert (tmp_path / "소리문.musicxml").exists()


def test_여러_문장(analyzer, composer):
    scores = [composer.compose(s)
              for s in analyzer.sentences("봄이 왔다. 꽃이 핀다. 좋구나!")]
    assert len(scores) == 3
    assert all(sc.notes for sc in scores)
