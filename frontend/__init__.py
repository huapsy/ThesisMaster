from __future__ import annotations

from pathlib import Path


_SRC_FRONTEND_ROOT = (Path(__file__).resolve().parents[1] / "src" / "frontend").resolve()
__path__ = [str(_SRC_FRONTEND_ROOT)]
