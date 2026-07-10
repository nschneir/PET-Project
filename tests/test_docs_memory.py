import os
import shutil
import struct
from pathlib import Path

import pytest

from petlib.session import Session
from petlib.text import ascii_to_petscii
from tests.vice_helpers import wait_for_text

REF = Path("skills/pet-development/references")


def test_docs_exist_and_state_vectors():
    mm = (REF / "memory-maps.md").read_text()
    for needle in ("FFFA", "FFFC", "FFFE", "8000-83E7", "E810", "E880"):
        assert needle in mm
    zp = (REF / "zero-page.md").read_text()
    for needle in ("TXTTAB", "VARTAB", "28/29", "026F"):
        assert needle in zp


@pytest.mark.vice
@pytest.mark.skipif(
    not (shutil.which("xpet") or os.environ.get("PET_TOOLS_XPET")),
    reason="xpet not installed",
)
def test_zero_page_chain_and_vectors_live(tmp_path, monkeypatch):
    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))
    s = Session.launch(model="pet4032", name="zp", headless=True, warp=True)
    try:
        wait_for_text(s, "READY.")
        with s.monitor() as mon:
            try:
                mon.keyboard_feed(ascii_to_petscii('10 a=1\n'))
            finally:
                mon.resume()
        wait_for_text(s, "10 A=1")
        with s.monitor() as mon:
            try:
                zp = mon.memory_read(0x28, 10)
                reset_vec = mon.memory_read(0xFFFC, 2)
            finally:
                mon.resume()
        txttab, vartab, arytab, strend, fretop = struct.unpack("<5H", zp)
        assert txttab == 0x0401                    # doc claim: TXTTAB = $0401
        assert txttab < vartab <= arytab <= strend <= fretop
        assert vartab - txttab > 5                 # our one-liner is in there
        reset = struct.unpack("<H", reset_vec)[0]
        assert 0xF000 <= reset <= 0xFFFF           # doc claim: kernal reset vector
    finally:
        s.stop()


@pytest.mark.vice
@pytest.mark.skipif(
    not (shutil.which("xpet") or os.environ.get("PET_TOOLS_XPET")),
    reason="xpet not installed",
)
def test_book_sourced_facts_live(tmp_path, monkeypatch):
    """Assert the West-sourced BASIC 4 facts in the reference docs against a
    real running machine: jiffy clock location/direction, IRQ RAM vector,
    hardware vector targets, and a kernal jump-table target."""
    import time

    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))
    s = Session.launch(model="pet4032", name="facts", headless=True, warp=True)
    try:
        wait_for_text(s, "READY.")
        with s.monitor() as mon:
            try:
                ti1 = mon.memory_read(0x8D, 3)
            finally:
                mon.resume()
        time.sleep(0.5)
        with s.monitor() as mon:
            try:
                ti2 = mon.memory_read(0x8D, 3)
                irq_ram = mon.memory_read(0x90, 2)
                vectors = mon.memory_read(0xFFFA, 6)
                open_jmp = mon.memory_read(0xFFC0, 3)
            finally:
                mon.resume()
        # TI at $8D-$8F, most-significant byte FIRST, ticking upward (doc: zero-page.md)
        t1 = (ti1[0] << 16) | (ti1[1] << 8) | ti1[2]
        t2 = (ti2[0] << 16) | (ti2[1] << 8) | ti2[2]
        assert t2 > t1, f"jiffy clock not ticking MSB-first at $8D: {ti1.hex()} -> {ti2.hex()}"
        # IRQ RAM vector ($90) = $E455 on BASIC 4 (doc: zero-page.md, rom-routines.md)
        assert struct.unpack("<H", irq_ram)[0] == 0xE455
        # hardware vectors NMI/RESET/IRQ = FD49/FD16/E442 on BASIC 4 (doc: rom-routines.md)
        nmi, reset, irq = struct.unpack("<3H", vectors)
        assert (nmi, reset, irq) == (0xFD49, 0xFD16, 0xE442)
        # kernal OPEN at $FFC0 is JMP $F560 on BASIC 4 (doc: rom-routines.md)
        assert open_jmp == bytes([0x4C, 0x60, 0xF5])
    finally:
        s.stop()


@pytest.mark.vice
@pytest.mark.skipif(
    not (shutil.which("xpet") or os.environ.get("PET_TOOLS_XPET")),
    reason="xpet not installed",
)
def test_basic1_jiffy_clock_location_live(tmp_path, monkeypatch):
    """BASIC 1 (pet2001) keeps TI at $0200-$0202, not $8D (doc: zero-page.md)."""
    import time

    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))
    s = Session.launch(model="pet2001", name="b1", headless=True, warp=True)
    try:
        wait_for_text(s, "READY.")
        with s.monitor() as mon:
            try:
                ti1 = mon.memory_read(0x0200, 3)
            finally:
                mon.resume()
        time.sleep(0.5)
        with s.monitor() as mon:
            try:
                ti2 = mon.memory_read(0x0200, 3)
            finally:
                mon.resume()
        t1 = (ti1[0] << 16) | (ti1[1] << 8) | ti1[2]
        t2 = (ti2[0] << 16) | (ti2[1] << 8) | ti2[2]
        assert t2 > t1, f"BASIC 1 jiffy clock not ticking at $0200: {ti1.hex()} -> {ti2.hex()}"
    finally:
        s.stop()
