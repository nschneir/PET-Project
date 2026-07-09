"""Declarative YAML test runner (spec §8).

A test boots a fresh warp session, optionally loads a program (autostart),
then executes wait/key/assert steps. Demos (spec §8.1) run through the same
engine via demo_test(). Fail-fast; the failure screen is captured for
debugging.
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass
from pathlib import Path

import yaml

from .basic import tokenize
from .build import build_asm
from .machines import get_profile
from .screen import read_screen_text
from .session import Session
from .text import ascii_to_petscii, screen_to_text


class TestError(Exception):
    __test__ = False  # not a pytest test class despite the Test* name


_STEP_KINDS = ("wait", "key", "assert")


def _num(v) -> int:
    if isinstance(v, int):
        return v
    s = str(v).strip()
    if s.startswith("$"):
        return int(s[1:], 16)
    if s.lower().startswith("0x"):
        return int(s, 16)
    return int(s)


def load_test(path: str | Path) -> dict:
    path = Path(path)
    spec = yaml.safe_load(path.read_text())
    if not isinstance(spec, dict):
        raise TestError(f"{path}: test file must be a YAML mapping")
    spec.setdefault("name", path.stem)
    spec.setdefault("machine", "pet4032")
    spec.setdefault("timeout", 30)
    spec.setdefault("autorun", True)
    spec.setdefault("steps", [])
    get_profile(spec["machine"])  # raises KeyError listing known models
    if spec.get("program"):
        prog = (path.parent / spec["program"]).resolve()
        if not prog.exists():
            raise TestError(f"{path}: program {prog} not found")
        spec["program"] = str(prog)
    for i, step in enumerate(spec["steps"], start=1):
        if (not isinstance(step, dict) or len(step) != 1
                or next(iter(step)) not in _STEP_KINDS):
            raise TestError(
                f"{path}: step {i} must be a single {'/'.join(_STEP_KINDS)} mapping"
            )
    return spec


def demo_test(demo_dir: str | Path) -> dict:
    demo_dir = Path(demo_dir)
    prog = next(
        (demo_dir / n for n in ("program.bas", "program.s") if (demo_dir / n).exists()),
        None,
    )
    expect = demo_dir / "expect.txt"
    if prog is None or not expect.exists():
        raise TestError(
            f"{demo_dir}: not a demo directory (needs program.bas/.s and expect.txt)"
        )
    steps = [{"wait": {"text": ln}} for ln in expect.read_text().splitlines() if ln.strip()]
    return {"name": demo_dir.name, "machine": "pet4032", "timeout": 45,
            "autorun": True, "program": str(prog.resolve()), "steps": steps}
