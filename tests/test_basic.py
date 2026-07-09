from pathlib import Path
from unittest.mock import patch

import pytest
import shutil

from petlib.basic import PETCAT_DIALECTS, BasicError, detokenize, tokenize


def test_dialect_map():
    assert PETCAT_DIALECTS == {"1.0": "1p", "2.0": "2", "4.0": "40"}


def test_tokenize_command_line(tmp_path):
    src, out = tmp_path / "a.bas", tmp_path / "a.prg"
    src.write_text('10 print "hi"\n')
    captured = {}

    def fake_run(cmd, **kw):
        captured["cmd"] = cmd
        out.write_bytes(b"\x01\x04")

        class R:
            returncode = 0
            stderr = ""

        return R()

    with patch("petlib.basic.subprocess.run", side_effect=fake_run), \
         patch("petlib.basic._petcat", return_value="petcat"):
        tokenize(src, out, "4.0")
    assert captured["cmd"] == ["petcat", "-w40", "-o", str(out), "--", str(src)]


def test_missing_petcat_message(monkeypatch):
    monkeypatch.delenv("PET_TOOLS_PETCAT", raising=False)
    monkeypatch.setattr("petlib.basic.shutil.which", lambda n: None)
    with pytest.raises(BasicError, match="[Ii]nstall"):
        tokenize(Path("x.bas"), Path("x.prg"), "4.0")


needs_petcat = pytest.mark.skipif(shutil.which("petcat") is None, reason="petcat not installed")


@needs_petcat
def test_real_petcat_roundtrip(tmp_path):
    src = tmp_path / "demo.bas"
    src.write_text('10 print "hello"\n20 print 2+2\n')
    prg = tokenize(src, tmp_path / "demo.prg", "4.0")
    data = prg.read_bytes()
    assert data[:2] == b"\x01\x04"      # load address $0401
    assert b"\x99" in data              # PRINT token
    listing = detokenize(prg, "4.0")
    assert 'print "hello"' in listing
    assert "2+2" in listing
