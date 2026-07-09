import os
import stat
from pathlib import Path

import pytest

from petlib.build import BuildError, BuildResult, build_asm, linker_config


def test_linker_config_contents():
    cfg = linker_config(0x0401)
    assert "$0401" in cfg
    for seg in ("LOADADDR", "EXEHDR", "CODE", "HEADER", "MAIN"):
        assert seg in cfg


def _stub_tool(dir: Path, name: str, body: str) -> Path:
    p = dir / name
    p.write_text("#!/usr/bin/env python3\n" + body)
    p.chmod(p.stat().st_mode | stat.S_IEXEC)
    return p


def test_build_asm_invokes_toolchain(tmp_path, monkeypatch):
    ca65 = _stub_tool(tmp_path, "ca65", (
        "import sys, pathlib\n"
        "a = sys.argv[1:]\n"
        "pathlib.Path(a[a.index('-o')+1]).write_bytes(b'OBJ')\n"
        "pathlib.Path(__file__).with_name('ca65.args').write_text(' '.join(a))\n"
    ))
    ld65 = _stub_tool(tmp_path, "ld65", (
        "import sys, pathlib\n"
        "a = sys.argv[1:]\n"
        "pathlib.Path(a[a.index('-o')+1]).write_bytes(b'\\x01\\x04PRG')\n"
        "pathlib.Path(a[a.index('-Ln')+1]).write_text('al 00040D .start\\n')\n"
        "pathlib.Path(__file__).with_name('ld65.args').write_text(' '.join(a))\n"
    ))
    monkeypatch.setenv("PET_TOOLS_CA65", str(ca65))
    monkeypatch.setenv("PET_TOOLS_LD65", str(ld65))

    src = tmp_path / "prog.s"
    src.write_text("; test\n")
    res = build_asm(src)
    assert isinstance(res, BuildResult)
    assert res.prg == tmp_path / "prog.prg" and res.prg.read_bytes()[:2] == b"\x01\x04"
    assert res.labels == tmp_path / "prog.lbl" and "start" in res.labels.read_text()
    ca65_args = (tmp_path / "ca65.args").read_text()
    assert str(src) in ca65_args
    assert "-g" in ca65_args.split()
    ld_args = (tmp_path / "ld65.args").read_text()
    assert "-C" in ld_args and "-Ln" in ld_args


def test_build_error_includes_stderr(tmp_path, monkeypatch):
    bad = _stub_tool(tmp_path, "ca65", "import sys; sys.stderr.write('prog.s(3): syntax error'); sys.exit(1)\n")
    monkeypatch.setenv("PET_TOOLS_CA65", str(bad))
    monkeypatch.setenv("PET_TOOLS_LD65", str(bad))
    src = tmp_path / "prog.s"
    src.write_text("bogus\n")
    with pytest.raises(BuildError, match="syntax error"):
        build_asm(src)


def test_missing_tool_message(monkeypatch):
    monkeypatch.delenv("PET_TOOLS_CA65", raising=False)
    monkeypatch.setattr("petlib.build.shutil.which", lambda n: None)
    with pytest.raises(BuildError, match="[Ii]nstall"):
        build_asm(Path("x.s"))
