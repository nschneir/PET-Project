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
