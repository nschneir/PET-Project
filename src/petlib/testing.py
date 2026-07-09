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


@dataclass
class StepResult:
    index: int
    kind: str
    ok: bool
    detail: str


@dataclass
class TestResult:
    __test__ = False  # not a pytest test class despite the Test* name
    name: str
    machine: str
    passed: bool
    steps: list[StepResult]
    elapsed: float
    screen: str
    session_name: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "machine": self.machine, "passed": self.passed,
            "elapsed": self.elapsed,
            "steps": [{"index": s.index, "kind": s.kind, "ok": s.ok,
                       "detail": s.detail} for s in self.steps],
            "screen": self.screen,
        }


def _prepare(program: str, profile) -> Path:
    src = Path(program)
    ext = src.suffix.lower()
    if ext == ".prg":
        return src
    if ext == ".bas":
        return tokenize(src, src.with_suffix(".prg"), profile.basic_version)
    if ext == ".s":
        return build_asm(src, basic_start=profile.basic_start).prg
    raise TestError(f"cannot run {ext!r} programs (use .bas, .s, or .prg)")


def _screen(session) -> str:
    with session.monitor() as mon:
        try:
            return read_screen_text(mon, session.profile)
        finally:
            mon.resume()


def _wait_screen(session, pred, timeout: float) -> tuple[bool, str]:
    deadline = time.monotonic() + timeout
    text = ""
    while time.monotonic() < deadline:
        text = _screen(session)
        if pred(text):
            return True, text
        time.sleep(0.3)
    return False, text


def _loaded(text: str) -> bool:
    return "LOADING" in text and text.rfind("READY.") > text.rfind("LOADING")


def _do_step(session, kind: str, arg, default_timeout: float) -> tuple[bool, str]:
    if kind == "key":
        with session.monitor() as mon:
            try:
                mon.keyboard_feed(ascii_to_petscii(str(arg)))
            finally:
                mon.resume()
        return True, f"typed {arg!r}"

    if kind == "wait":
        timeout = arg.get("timeout", default_timeout)
        if "text" in arg:
            ok, _ = _wait_screen(session, lambda t: arg["text"] in t, timeout)
            return ok, (f"text {arg['text']!r} seen" if ok
                        else f"text {arg['text']!r} not seen in {timeout}s")
        if "mem" in arg:
            addr, want = _num(arg["mem"]), _num(arg["equals"])
            deadline = time.monotonic() + timeout
            val = None
            while time.monotonic() < deadline:
                with session.monitor() as mon:
                    try:
                        val = mon.memory_read(addr, 1)[0]
                    finally:
                        mon.resume()
                if val == want:
                    return True, f"mem ${addr:04x} == {want}"
                time.sleep(0.3)
            return False, f"mem ${addr:04x} was {val}, wanted {want} ({timeout}s)"
        raise TestError(f"wait step needs 'text' or 'mem': {arg}")

    # kind == "assert"
    if "screen" in arg:
        text = _screen(session)
        ok = arg["screen"] in text
        return ok, (f"screen contains {arg['screen']!r}" if ok
                    else f"screen missing {arg['screen']!r}")
    if "mem" in arg:
        addr = _num(arg["mem"])
        with session.monitor() as mon:
            try:
                if "equals_text" in arg:
                    want_t = str(arg["equals_text"])
                    data = mon.memory_read(addr, len(want_t))
                else:
                    want = arg["equals"]
                    want_b = (bytes(want) if isinstance(want, list)
                              else bytes([_num(want)]))
                    data = mon.memory_read(addr, len(want_b))
            finally:
                mon.resume()
        if "equals_text" in arg:
            got = screen_to_text(data, len(want_t))
            ok = got == want_t
            return ok, f"mem ${addr:04x} text {got!r}" + ("" if ok else f" != {want_t!r}")
        ok = data == want_b
        return ok, f"mem ${addr:04x} = {data.hex()}" + ("" if ok else f" != {want_b.hex()}")
    if "reg" in arg:
        with session.monitor() as mon:
            try:
                regs = mon.registers()
            finally:
                mon.resume()
        name = str(arg["reg"]).upper()
        if name not in regs:
            return False, f"no register {name!r} (have {', '.join(sorted(regs))})"
        val = regs[name]
        if "equals" in arg:
            want = _num(arg["equals"])
            ok = val == want
            return ok, f"{name}={val:#06x}" + ("" if ok else f" != {want:#06x}")
        lo, hi = (_num(x) for x in arg["in_range"])
        ok = lo <= val <= hi
        return ok, (f"{name}={val:#06x} in [{lo:#06x}, {hi:#06x}]" if ok
                    else f"{name}={val:#06x} not in [{lo:#06x}, {hi:#06x}]")
    raise TestError(f"assert step needs 'screen', 'mem', or 'reg': {arg}")


def run_test(spec: dict, launch=Session.launch) -> TestResult:
    t0 = time.monotonic()
    profile = get_profile(spec["machine"])
    session_name = f"t{uuid.uuid4().hex[:6]}"
    steps: list[StepResult] = []
    screen_text = ""
    session = launch(model=spec["machine"], name=session_name,
                     headless=True, warp=True)
    try:
        ok, screen_text = _wait_screen(session, lambda t: "READY." in t, 45.0)
        if not ok:
            raise TestError(f"machine never reached READY.; screen:\n{screen_text}")
        if spec.get("program"):
            prg = _prepare(spec["program"], profile)
            with session.monitor() as mon:
                try:
                    mon.autostart(Path(prg).resolve(), run=spec["autorun"])
                finally:
                    mon.resume()
            if not spec["autorun"]:
                ok, screen_text = _wait_screen(session, _loaded, spec["timeout"] + 15)
                if not ok:
                    raise TestError(f"program never finished loading; screen:\n{screen_text}")
        passed = True
        for i, step in enumerate(spec["steps"], start=1):
            kind = next(iter(step))
            ok, detail = _do_step(session, kind, step[kind], spec["timeout"])
            steps.append(StepResult(index=i, kind=kind, ok=ok, detail=detail))
            if not ok:
                passed = False
                break
        screen_text = _screen(session)
        return TestResult(name=spec["name"], machine=spec["machine"], passed=passed,
                          steps=steps, elapsed=round(time.monotonic() - t0, 2),
                          screen=screen_text, session_name=session_name)
    finally:
        session.stop()
