import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from petlib.cli import main
from petlib.protocol import CP_EXEC, CP_LOAD, CP_STORE, Checkpoint


def _ck(number=1, start=0x040D, op=CP_EXEC, hits=0):
    return Checkpoint(number=number, hit=False, start=start, end=start, stop=True,
                      enabled=True, op=op, temporary=False, hit_count=hits,
                      ignore_count=0, has_condition=False, memspace=0)


def _fake(labels=None):
    fake = Mock()
    fake.name, fake.model, fake.labels = "pet4032", "pet4032", labels
    mon = Mock()
    fake.monitor.return_value.__enter__ = Mock(return_value=mon)
    fake.monitor.return_value.__exit__ = Mock(return_value=False)
    return fake, mon


def test_break_add_symbolic(tmp_path):
    lbl = tmp_path / "p.lbl"
    lbl.write_text("al C:040d .start\n")
    fake, mon = _fake(labels=str(lbl))
    mon.checkpoint_set.return_value = _ck()
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "break", "add", "start"])
    assert r.exit_code == 0, r.output
    mon.checkpoint_set.assert_called_once_with(0x040D, op=CP_EXEC, temporary=False)
    out = json.loads(r.output)
    assert out["id"] == 1 and "start" in out["address"]
    mon.resume.assert_called_once()


def test_break_add_with_condition():
    fake, mon = _fake()
    mon.checkpoint_set.return_value = _ck(number=4)
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["break", "add", "$040d", "--condition", "A != 0"])
    assert r.exit_code == 0, r.output
    mon.condition_set.assert_called_once_with(4, "A != 0")


def test_break_add_unknown_symbol_fails():
    fake, mon = _fake()
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "break", "add", "nosuch"])
    assert r.exit_code == 1
    assert "nosuch" in json.loads(r.output)["error"]


def test_break_list_and_remove():
    fake, mon = _fake()
    mon.checkpoint_list.return_value = [_ck(number=1, hits=3), _ck(number=2, start=0x8000)]
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "break", "list"])
        assert [c["id"] for c in json.loads(r.output)["breakpoints"]] == [1, 2]
        r2 = CliRunner().invoke(main, ["break", "remove", "2"])
    assert r2.exit_code == 0
    mon.checkpoint_delete.assert_called_once_with(2)


def test_watch_add_store_only_with_length():
    fake, mon = _fake()
    mon.checkpoint_set.return_value = _ck(op=CP_STORE)
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["watch", "add", "$8000", "--store", "--length", "40"])
    assert r.exit_code == 0, r.output
    mon.checkpoint_set.assert_called_once_with(0x8000, 0x8000 + 39, op=CP_STORE)


def test_watch_add_default_both():
    fake, mon = _fake()
    mon.checkpoint_set.return_value = _ck(op=CP_LOAD | CP_STORE)
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["watch", "add", "$8000"])
    assert r.exit_code == 0
    mon.checkpoint_set.assert_called_once_with(0x8000, 0x8000, op=CP_LOAD | CP_STORE)
