import json
from pathlib import Path
from unittest.mock import patch

from click.testing import CliRunner

from petlib.cli import main
from petlib.testing import StepResult, TestResult


def _result(passed=True, name="t"):
    return TestResult(
        name=name, machine="pet4032", passed=passed,
        steps=[StepResult(index=1, kind="wait", ok=passed,
                          detail="text 'X' seen" if passed else "text 'X' not seen in 2s")],
        elapsed=1.5, screen="READY.\nX" if passed else "READY.",
        session_name="t123456",
    )


def test_run_pass_exit_zero(tmp_path):
    f = tmp_path / "a.yaml"
    f.write_text("steps: []\n")
    with patch("petlib.cli.run_test", return_value=_result(True)) as rt, \
         patch("petlib.cli.load_test", return_value={"name": "a"}) as lt:
        r = CliRunner().invoke(main, ["--json", "test", "run", str(f)])
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["passed"] is True and out["tests"][0]["name"] == "t"
    lt.assert_called_once_with(f)
    rt.assert_called_once_with({"name": "a"})


def test_run_fail_exit_one(tmp_path):
    f = tmp_path / "a.yaml"
    f.write_text("steps: []\n")
    with patch("petlib.cli.run_test", return_value=_result(False)), \
         patch("petlib.cli.load_test", return_value={"name": "a"}):
        r = CliRunner().invoke(main, ["--json", "test", "run", str(f)])
    assert r.exit_code == 1
    assert json.loads(r.output)["passed"] is False


def test_run_load_error(tmp_path):
    f = tmp_path / "a.yaml"
    f.write_text("program: nosuch.bas\n")
    r = CliRunner().invoke(main, ["--json", "test", "run", str(f)])
    assert r.exit_code == 1
    assert "nosuch" in json.loads(r.output)["error"]


def test_programs_runs_each_directory(tmp_path):
    for d in ("alpha", "beta"):
        (tmp_path / d).mkdir()
        (tmp_path / d / "expect.txt").write_text("X\n")
        (tmp_path / d / "program.bas").write_text("10 rem\n")
    results = {"alpha": _result(True, "alpha"), "beta": _result(False, "beta")}
    with patch("petlib.cli.program_test", side_effect=lambda p: {"name": Path(p).name}) as dt, \
         patch("petlib.cli.run_test", side_effect=lambda s: results[s["name"]]):
        r = CliRunner().invoke(main, ["--json", "test", "programs", str(tmp_path)])
    assert r.exit_code == 1          # beta failed
    out = json.loads(r.output)
    assert [t["name"] for t in out["tests"]] == ["alpha", "beta"]
    assert out["passed"] is False
    assert dt.call_count == 2
