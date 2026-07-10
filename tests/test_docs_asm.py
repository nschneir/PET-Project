import os
import re
import shutil
from pathlib import Path

import pytest

from petlib.build import build_asm

SKILL = Path("skills/6502-assembly/SKILL.md")


def test_hardware_doc_base_addresses():
    doc = Path("skills/pet-development/references/hardware.md").read_text()
    for needle in ("E810", "E820", "E840", "E880"):
        assert needle in doc


@pytest.mark.skipif(
    shutil.which("ca65") is None and not os.environ.get("PET_TOOLS_CA65"),
    reason="cc65 not installed",
)
def test_skill_skeleton_assembles(tmp_path):
    text = SKILL.read_text()
    blocks = re.findall(r"```(?:asm|ca65)\n(.*?)```", text, re.S)
    assert blocks, "6502-assembly SKILL.md must contain an ```asm skeleton block"
    src = tmp_path / "skeleton.s"
    src.write_text(blocks[0])
    res = build_asm(src)
    assert res.prg.read_bytes()[:2] == b"\x01\x04"
