from unittest.mock import Mock, patch

import pytest

from petlib.monitor import StopInfo
from petlib.protocol import CP_EXEC, CP_STORE, Checkpoint
from tests.test_mcp_scaffold import call_tool


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))


def _fake(labels=None):
    s = Mock()
    s.name, s.model, s.labels = "pet4032", "pet4032", labels
    s.profile.basic_version = "4.0"
    s.profile.screen_cols = 40
    mon = Mock()
    s.monitor.return_value.__enter__ = Mock(return_value=mon)
    s.monitor.return_value.__exit__ = Mock(return_value=False)
    return s, mon


def _ck(number=1, start=0x040D, op=CP_EXEC, hit=False):
    return Checkpoint(number=number, hit=hit, start=start, end=start, stop=True,
                      enabled=True, op=op, temporary=False, hit_count=0,
                      ignore_count=0, has_condition=False, memspace=0)


def test_break_add_symbolic(tmp_path):
    lbl = tmp_path / "p.lbl"
    lbl.write_text("al C:040d .start\n")
    s, mon = _fake(labels=str(lbl))
    mon.checkpoint_set.return_value = _ck()
    with patch("petlib.mcp_server.Session") as S:
        S.attach.return_value = s
        err, out = call_tool("pet_break_add", {"ref": "start"})
    assert err is False and out["id"] == 1
    mon.checkpoint_set.assert_called_once_with(0x040D, op=CP_EXEC, temporary=False)
    mon.release.assert_called_once()


def test_watch_add_store(tmp_path):
    s, mon = _fake()
    mon.checkpoint_set.return_value = _ck(op=CP_STORE, start=0x8000)
    with patch("petlib.mcp_server.Session") as S:
        S.attach.return_value = s
        err, out = call_tool("pet_watch_add",
                             {"ref": "$8000", "on_store": True, "length": 40})
    assert err is False
    mon.checkpoint_set.assert_called_once_with(0x8000, 0x8000 + 39, op=CP_STORE)


def test_step_stays_stopped():
    s, mon = _fake()
    mon.step.return_value = {"PC": 0x0412}
    with patch("petlib.mcp_server.Session") as S:
        S.attach.return_value = s
        err, out = call_tool("pet_step", {"count": 2})
    assert err is False and out["registers"]["PC"] == 0x0412 and out["stopped"] is True
    mon.step.assert_called_once_with(2, over=False)
    mon.resume.assert_not_called()


def test_until_timeout_returns_error():
    s, mon = _fake()
    mon.checkpoint_set.return_value = _ck(start=0x2000)
    mon.wait_for_stop.return_value = None
    mon.checkpoint_list.return_value = []
    with patch("petlib.mcp_server.Session") as S:
        S.attach.return_value = s
        err, out = call_tool("pet_until", {"ref": "$2000", "timeout": 1})
    assert err is True and "timeout" in out["raw"].lower()


def test_wait_break_fires():
    s, mon = _fake()
    mon.checkpoint_list.return_value = []
    mon.wait_for_stop.return_value = StopInfo(pc=0x040D, checkpoint=5)
    mon.registers.return_value = {"PC": 0x040D}
    with patch("petlib.mcp_server.Session") as S:
        S.attach.return_value = s
        err, out = call_tool("pet_wait_break", {"timeout": 2})
    assert err is False and out["fired"] == "break" and out["checkpoint"] == 5


def test_wait_text_timeout_not_error():
    s, mon = _fake()
    with patch("petlib.mcp_server.Session") as S, \
         patch("petlib.ops.read_screen_text", return_value="STUCK"), \
         patch("petlib.ops.time.sleep"):
        S.attach.return_value = s
        err, out = call_tool("pet_wait_text", {"text": "NEVER", "timeout": 0.3})
    assert err is False
    assert out["fired"] is None and "STUCK" in out["screen"]
