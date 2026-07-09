import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from petlib.cli import main
from petlib.session import SessionError


def _fake_session(name="pet4032", port=6502):
    s = Mock()
    s.name, s.pid, s.port, s.model = name, 1234, port, "pet4032"
    return s


def test_session_start_json():
    with patch("petlib.cli.Session") as S:
        S.launch.return_value = _fake_session()
        r = CliRunner().invoke(main, ["--json", "session", "start", "--model", "pet4032"])
    assert r.exit_code == 0, r.output
    out = json.loads(r.output)
    assert out["name"] == "pet4032" and out["port"] == 6502
    S.launch.assert_called_once_with(
        model="pet4032", name=None, headless=False, warp=False, disk8=None
    )


def test_session_list_human():
    with patch("petlib.cli.Session") as S:
        S.list_all.return_value = [_fake_session()]
        r = CliRunner().invoke(main, ["session", "list"])
    assert r.exit_code == 0
    assert "pet4032" in r.output and "6502" in r.output


def test_session_stop_by_name():
    fake = _fake_session()
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["session", "stop", "pet4032"])
    assert r.exit_code == 0
    S.attach.assert_called_once_with("pet4032")
    fake.stop.assert_called_once()


def test_session_error_json_exit_code():
    with patch("petlib.cli.Session") as S:
        S.attach.side_effect = SessionError("no PET session running. Start one with: pet session start")
        r = CliRunner().invoke(main, ["--json", "session", "stop"])
    assert r.exit_code == 1
    assert "no PET session" in json.loads(r.output)["error"]


def test_session_reset_resumes():
    fake = _fake_session()
    mon = Mock()
    fake.monitor.return_value.__enter__ = Mock(return_value=mon)
    fake.monitor.return_value.__exit__ = Mock(return_value=False)
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["session", "reset", "--hard"])
    assert r.exit_code == 0
    mon.reset.assert_called_once_with(hard=True)
    mon.resume.assert_called_once()
