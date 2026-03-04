from __future__ import annotations

import re
from pathlib import Path


def test_requires_python_is_311_or_newer() -> None:
    pyproject = Path(__file__).resolve().parents[1] / "pyproject.toml"
    text = pyproject.read_text(encoding="utf-8")
    match = re.search(r'requires-python\s*=\s*"(.*?)"', text)
    assert match is not None
    assert match.group(1).startswith(">=3.11")
