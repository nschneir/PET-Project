from pathlib import Path

import pytest

from petlib.testing import TestError, load_test


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
