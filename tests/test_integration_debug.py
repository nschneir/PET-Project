"""Live symbolic-debug-loop test: breakpoint in hello-asm, step, inspect, wait."""

import os
import shutil
from pathlib import Path

import pytest

from petlib.build import build_asm
from petlib.session import Session
from petlib.symbols import load_labels
from tests.vice_helpers import wait_for_text

pytestmark = [
    pytest.mark.vice,
    pytest.mark.skipif(
        not (shutil.which("xpet") or os.environ.get("PET_TOOLS_XPET")),
        reason="xpet not installed",
    ),
    pytest.mark.skipif(
        shutil.which("ca65") is None and not os.environ.get("PET_TOOLS_CA65"),
        reason="cc65 not installed",
    ),
]


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))
    s = Session.launch(model="pet4032", name="dbgtest", headless=True, warp=True)
    wait_for_text(s, "READY.")
    yield s
    s.stop()


def test_symbolic_debug_loop(session, tmp_path):
    # build with -g: local labels must be in the label file
    res = build_asm(Path("tests/programs/hello-asm/program.s"), out_prg=tmp_path / "dbg.prg")
    labels = load_labels(res.labels)
    assert {"start", "loop", "msg"} <= set(labels)
    session.set_labels_path(str(res.labels))

    # breakpoint at 'start', then autostart (checkpoints survive autostart)
    with session.monitor() as mon:
        try:
            ck = mon.checkpoint_set(labels["start"])
            mon.autostart(res.prg.resolve(), run=True)
        finally:
            mon.resume()

    # wait for the hit, inspect, step, read memory symbolically
    mon = session.monitor()
    try:
        hit = next((c for c in mon.checkpoint_list() if c.hit), None)
        if hit is None:
            mon.resume()
            info = mon.wait_for_stop(timeout=45.0)
            assert info is not None, "breakpoint never hit"
            assert info.checkpoint == ck.number
        regs = mon.registers()
        assert regs["PC"] == labels["start"]

        regs = mon.step(2)                       # ldx #0 ; lda msg,x
        assert regs["PC"] == labels["start"] + 5

        msg = mon.memory_read(labels["msg"], 14)
        assert msg == b"HELLO FROM ASM"

        mon.checkpoint_delete(ck.number)
        mon.resume()
    finally:
        mon.close()

    # program completes after resume
    wait_for_text(session, "HELLO FROM ASM", timeout=30.0)


def test_watchpoint_on_screen_ram(session, tmp_path):
    res = build_asm(Path("tests/programs/hello-asm/program.s"), out_prg=tmp_path / "w.prg")
    from petlib.protocol import CP_STORE

    with session.monitor() as mon:
        try:
            ck = mon.checkpoint_set(0x8000, 0x83E7, op=CP_STORE)
            mon.autostart(res.prg.resolve(), run=True)
        finally:
            mon.resume()

    mon = session.monitor()
    try:
        hit = next((c for c in mon.checkpoint_list() if c.hit), None)
        if hit is None:
            mon.resume()
            info = mon.wait_for_stop(timeout=45.0)
            assert info is not None, "watchpoint never hit"
        mon.checkpoint_delete(ck.number)
        mon.resume()
    finally:
        mon.close()
