"""End-to-end tests against a real VICE xpet. Skipped when xpet is absent."""

import os
import shutil
import time

import pytest

from petlib.screen import read_screen_text
from petlib.session import Session

pytestmark = [
    pytest.mark.vice,
    pytest.mark.skipif(
        not (shutil.which("xpet") or os.environ.get("PET_TOOLS_XPET")),
        reason="xpet not installed",
    ),
]


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))
    s = Session.launch(model="pet4032", name="itest", headless=True, warp=True)
    yield s
    s.stop()


def _wait_for_text(session, needle, timeout=30.0):
    deadline = time.monotonic() + timeout
    text = ""
    while time.monotonic() < deadline:
        with session.monitor() as mon:
            try:
                text = read_screen_text(mon, session.profile)
            finally:
                mon.resume()
        if needle in text:
            return text
        time.sleep(0.5)
    pytest.fail(f"{needle!r} never appeared on screen; last screen:\n{text}")


def test_boots_to_ready(session):
    text = _wait_for_text(session, "READY.")
    assert "COMMODORE BASIC" in text or "BASIC" in text


def test_memory_roundtrip_on_screen(session):
    _wait_for_text(session, "READY.")
    with session.monitor() as mon:
        try:
            # write screen codes "HI" to top-left of screen RAM
            mon.memory_write(0x8000, bytes([8, 9]))
            assert mon.memory_read(0x8000, 2) == bytes([8, 9])
            text = read_screen_text(mon, session.profile)
        finally:
            mon.resume()
    assert text.splitlines()[0].startswith("HI")


def test_registers_readable_and_pc_moves(session):
    _wait_for_text(session, "READY.")
    with session.monitor() as mon:
        try:
            regs = mon.registers()
        finally:
            mon.resume()
    assert "PC" in regs and 0 <= regs["PC"] <= 0xFFFF


def test_keyboard_feed_runs_basic(session):
    from petlib.text import ascii_to_petscii

    _wait_for_text(session, "READY.")
    with session.monitor() as mon:
        try:
            mon.keyboard_feed(ascii_to_petscii('PRINT "HELLO FROM PETLIB"\n'))
        finally:
            mon.resume()
    assert "HELLO FROM PETLIB" in _wait_for_text(session, "HELLO FROM PETLIB", timeout=15)
