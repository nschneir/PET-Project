from pathlib import Path

import pytest

from petlib.machines import get_profile
from petlib.testing import TestError, _prepare, load_test, program_test


def _write(tmp_path, text, name="t.yaml"):
    f = tmp_path / name
    f.write_text(text)
    return f


def test_defaults_applied(tmp_path):
    f = _write(tmp_path, "steps:\n  - key: \"RUN\\n\"\n")
    spec = load_test(f)
    assert spec["name"] == "t"
    assert spec["machine"] == "pet4032"
    assert spec["timeout"] == 30
    assert spec["autorun"] is True
    assert spec["steps"] == [{"key": "RUN\n"}]


def test_program_resolved_relative_to_yaml(tmp_path):
    prog = tmp_path / "prog.bas"
    prog.write_text('10 print "hi"\n')
    f = _write(tmp_path, "program: prog.bas\nsteps: []\n")
    spec = load_test(f)
    assert spec["program"] == str(prog.resolve())


def test_missing_program_rejected(tmp_path):
    f = _write(tmp_path, "program: nosuch.bas\n")
    with pytest.raises(TestError, match="nosuch"):
        load_test(f)


def test_bad_machine_rejected(tmp_path):
    f = _write(tmp_path, "machine: amiga500\nsteps: []\n")
    with pytest.raises(KeyError, match="amiga500"):
        load_test(f)


def test_bad_step_rejected(tmp_path):
    f = _write(tmp_path, "steps:\n  - frobnicate: 1\n")
    with pytest.raises(TestError, match="step 1"):
        load_test(f)


def test_spec_example_shape(tmp_path):
    prog = tmp_path / "hello.bas"
    prog.write_text('10 print "hello, world"\n')
    f = _write(tmp_path, """\
name: hello-world
machine: pet4032
program: hello.bas
autorun: false
timeout: 30
steps:
  - wait: { text: "READY." }
  - key: "RUN\\n"
  - wait: { text: "HELLO, WORLD", timeout: 5 }
  - assert: { mem: "$8000", equals_text: "HELLO, WORLD" }
  - assert: { reg: pc, in_range: ["$C000", "$E000"] }
""")
    spec = load_test(f)
    assert spec["autorun"] is False
    assert len(spec["steps"]) == 5


def test_program_test_synthesis():
    spec = program_test(Path("tests/programs/hello-basic"))
    assert spec["name"] == "hello-basic"
    assert spec["autorun"] is True
    assert spec["program"].endswith("tests/programs/hello-basic/program.bas")
    assert spec["steps"] == [
        {"wait": {"text": "HELLO FROM BASIC"}},
        {"wait": {"text": "2+2= 4"}},
    ]


def test_program_test_rejects_non_program_dir(tmp_path):
    with pytest.raises(TestError, match="example-program"):
        program_test(tmp_path)


def test_load_test_rejects_non_mapping(tmp_path):
    f = tmp_path / "bad.yaml"
    f.write_text("- just\n- a list\n")
    with pytest.raises(TestError, match="YAML mapping"):
        load_test(f)


def test_prepare_prg_passthrough(tmp_path):
    prg = tmp_path / "x.prg"
    prg.write_bytes(b"\x01\x04")
    assert _prepare(str(prg), get_profile("pet4032")) == prg


def test_prepare_unknown_extension(tmp_path):
    with pytest.raises(TestError, match="cannot run"):
        _prepare(str(tmp_path / "x.txt"), get_profile("pet4032"))
