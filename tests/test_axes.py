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


def test_서명_도약의_거칢이_단조다():
    """등급이 오를수록 서명 도약이 거칠어진다 — 익숙함의 축."""
    sys.path.insert(0, str(ROOT))
    from sorimun.core import codes as C
    from sorimun.core.harmony import _IC_ROUGHNESS, _interval_class

    rough = [_IC_ROUGHNESS[_interval_class(v)] for v in C.TIER_LEAP]
    assert all(a < b for a, b in zip(rough, rough[1:]))
    assert rough[-1] / rough[0] > 4
