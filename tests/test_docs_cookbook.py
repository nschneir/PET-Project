"""Every cookbook recipe must build — and run correctly on a real PET."""

import os
import re
import shutil
from pathlib import Path

import pytest

from petlib.basic import tokenize
from petlib.build import build_asm
from petlib.testing import run_test

COOKBOOK = Path("skills/pet-development/references/cookbook.md")


def _blocks(lang: str) -> list[str]:
    return re.findall(rf"```{lang}\n(.*?)```", COOKBOOK.read_text(), re.S)


def test_cookbook_has_recipes():
    assert len(_blocks("basic")) >= 3
    assert len(_blocks("asm")) >= 2


@pytest.mark.skipif(shutil.which("petcat") is None, reason="petcat not installed")
def test_basic_recipes_tokenize(tmp_path):
    for i, block in enumerate(_blocks("basic")):
        src = tmp_path / f"r{i}.bas"
        src.write_text(block)
        prg = tokenize(src, tmp_path / f"r{i}.prg", "4.0")
        assert prg.read_bytes()[:2] == b"\x01\x04"


@pytest.mark.skipif(
    shutil.which("ca65") is None and not os.environ.get("PET_TOOLS_CA65"),
    reason="cc65 not installed",
)
def test_asm_recipes_assemble(tmp_path):
    for i, block in enumerate(_blocks("asm")):
        src = tmp_path / f"r{i}.s"
        src.write_text(block)
        res = build_asm(src)
        assert res.prg.read_bytes()[:2] == b"\x01\x04"


# --- live: each recipe runs and behaves as the cookbook promises -----------

LIVE_RECIPES = [
    # (name, lang, block index, steps)
    ("basic-game-loop", "basic", 0, [
        {"wait": {"text": "PRESS Q TO QUIT"}},
        {"wait": {"text": "..."}},            # frames ticking
        {"key": "q"},
        {"wait": {"text": "BYE"}},
    ]),
    ("basic-poke-stars", "basic", 1, [
        {"wait": {"text": "DONE"}},
        # 32768 + 40*5 + 10 = $80D2 holds screen code 42 ('*')
        {"assert": {"mem": "$80D2", "equals": 42}},
    ]),
    ("basic-beep", "basic", 2, [
        {"wait": {"text": "BEEPED"}},
    ]),
    ("asm-ball", "asm", 0, [
        {"wait": {"text": "*"}},              # the ball is on screen
        {"key": "q"},
        {"wait": {"text": "READY."}},         # clean exit to BASIC
    ]),
    ("asm-beep", "asm", 1, [
        {"wait": {"text": "OK"}},
    ]),
]


@pytest.mark.vice
@pytest.mark.skipif(
    not (shutil.which("xpet") or os.environ.get("PET_TOOLS_XPET")),
    reason="xpet not installed",
)
@pytest.mark.parametrize("name,lang,idx,steps",
                         LIVE_RECIPES, ids=[r[0] for r in LIVE_RECIPES])
def test_cookbook_recipe_runs_live(tmp_path, monkeypatch, name, lang, idx, steps):
    if lang == "asm" and shutil.which("ca65") is None \
            and not os.environ.get("PET_TOOLS_CA65"):
        pytest.skip("cc65 not installed")
    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))
    src = tmp_path / f"{name}{'.bas' if lang == 'basic' else '.s'}"
    src.write_text(_blocks(lang)[idx])
    spec = {"name": name, "machine": "pet4032", "timeout": 30,
            "autorun": True, "program": str(src), "steps": steps}
    result = run_test(spec)
    assert result.passed, [s.detail for s in result.steps] + [result.screen]
