import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from petlib.cli import main
from petlib.monitor import StopInfo
from petlib.protocol import CP_EXEC, Checkpoint


def _fake(labels=None):
    fake = Mock()
    fake.name, fake.model, fake.labels = "pet4032", "pet4032", labels
    fake.profile.screen_cols = 40
    mon = Mock()
    fake.monitor.return_value.__enter__ = Mock(return_value=mon)
    fake.monitor.return_value.__exit__ = Mock(return_value=False)
    return fake, mon


def test_wait_requires_exactly_one_condition():
    fake, _ = _fake()
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "wait"])
        r2 = CliRunner().invoke(main, ["--json", "wait", "--text", "X", "--break"])
    assert r.exit_code == 1 and r2.exit_code == 1


def test_wait_text_fires():
    fake, mon = _fake()
    with patch("petlib.cli.Session") as S, \
         patch("petlib.ops.read_screen_text", side_effect=["LOADING", "READY."]):
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "wait", "--text", "READY.", "--timeout", "5"])
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["fired"] == "text"
    assert mon.release.call_count == 2   # one per poll


def test_wait_text_timeout_includes_screen():
    fake, mon = _fake()
    with patch("petlib.cli.Session") as S, \
         patch("petlib.ops.read_screen_text", return_value="STUCK"), \
         patch("petlib.ops.time.sleep"):
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "wait", "--text", "NEVER", "--timeout", "0.5"])
    assert r.exit_code == 1
    assert "STUCK" in json.loads(r.output)["error"]


def test_wait_mem_fires():
    fake, mon = _fake()
    mon.memory_read.side_effect = [b"\x00", b"\x2a"]
    with patch("petlib.cli.Session") as S, patch("petlib.ops.time.sleep"):
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "wait", "--mem", "$1000=42", "--timeout", "5"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["fired"] == "mem"


def test_wait_break_already_hit_returns_immediately(tmp_path):
    lbl = tmp_path / "p.lbl"
    lbl.write_text("al C:040d .start\n")
    fake, mon = _fake(labels=str(lbl))
    mon.checkpoint_list.return_value = [Checkpoint(
        number=3, hit=True, start=0x040D, end=0x040D, stop=True, enabled=True,
        op=CP_EXEC, temporary=False, hit_count=1, ignore_count=0,
        has_condition=False, memspace=0)]
    mon.registers.return_value = {"PC": 0x040D}
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "wait", "--break"])
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["fired"] == "break" and out["checkpoint"] == 3
    assert out["pc_symbol"] == "start"
    mon.wait_for_stop.assert_not_called()


def test_wait_break_listens_for_stop():
    fake, mon = _fake()
    mon.checkpoint_list.return_value = []
    mon.wait_for_stop.return_value = StopInfo(pc=0x1234, checkpoint=7)
    mon.registers.return_value = {"PC": 0x1234}
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "wait", "--break", "--timeout", "3"])
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["fired"] == "break" and out["checkpoint"] == 7
    mon.resume.assert_called_once()
