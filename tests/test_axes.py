"""두 축의 조화 — verify_axes 를 시험으로도 돈다."""

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def test_축_검증_전체():
    r = subprocess.run(
        [sys.executable, str(ROOT / "tools" / "verify_axes.py")],
        capture_output=True, text=True, timeout=120,
    )
    assert r.returncode == 0, r.stdout + r.stderr


def test_사다리가_고르다():
    """의미 화음의 거칢 계단이 성질마다 대체로 고르게 벌어져 있다."""
    sys.path.insert(0, str(ROOT))
    from sorimun.core.banks import BANKS
    from sorimun.core.harmony import Quality, dissonance

    for q in Quality:
        ds = [dissonance(BANKS.meaning[(t, q)].voicing) for t in range(6)]
        steps = [b - a for a, b in zip(ds, ds[1:])]
        assert min(steps) > 0
        # 가장 큰 계단이 가장 작은 계단의 4배를 넘지 않는다
        assert max(steps) / min(steps) < 4.0, (q, steps)
