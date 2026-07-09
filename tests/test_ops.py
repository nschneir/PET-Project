from unittest.mock import Mock, patch

import pytest

from petlib.monitor import StopInfo
from petlib.ops import parse_number, parse_ref, wait_for_break, wait_for_text
from petlib.protocol import CP_EXEC, Checkpoint


def _fake_session():
    s = Mock()
    s.profile.screen_cols = 40
    mon = Mock()
    s.monitor.return_value.__enter__ = Mock(return_value=mon)
    s.monitor.return_value.__exit__ = Mock(return_value=False)
    return s, mon


def test_parse_number_and_ref():
    assert parse_number("$8000") == 0x8000
    assert parse_ref({}, "0x1000") == 0x1000
    assert parse_ref({"start": 0x040D}, "start") == 0x040D
    with pytest.raises(KeyError):
        parse_ref({}, "nosuch")


def test_wait_for_text_fires_and_times_out():
    s, mon = _fake_session()
    with patch("petlib.ops.read_screen_text", side_effect=["A", "B READY."]):
        out = wait_for_text(s, "READY.", timeout=5)
    assert out["fired"] == "text"

    s2, _ = _fake_session()
    with patch("petlib.ops.read_screen_text", return_value="STUCK"), \
         patch("petlib.ops.time.sleep"):
        out2 = wait_for_text(s2, "Never", timeout=0.3)
    assert out2["fired"] is None and "STUCK" in out2["screen"]


def test_wait_for_break_already_hit():
    s, mon = _fake_session()
    mon.checkpoint_list.return_value = [Checkpoint(
        number=3, hit=True, start=0x040D, end=0x040D, stop=True, enabled=True,
        op=CP_EXEC, temporary=False, hit_count=1, ignore_count=0,
        has_condition=False, memspace=0)]
    mon.registers.return_value = {"PC": 0x040D}
    out = wait_for_break(s, timeout=1)
    assert out["fired"] == "break" and out["checkpoint"] == 3
    mon.wait_for_stop.assert_not_called()


def test_wait_for_break_listens():
    s, mon = _fake_session()
    mon.checkpoint_list.return_value = []
    mon.wait_for_stop.return_value = StopInfo(pc=0x1234, checkpoint=7)
    mon.registers.return_value = {"PC": 0x1234}
    out = wait_for_break(s, timeout=1)
    assert out["checkpoint"] == 7 and out["pc"] == 0x1234
    mon.resume.assert_called_once()
