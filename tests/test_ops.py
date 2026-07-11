from unittest.mock import Mock, patch

import pytest

from petlib.monitor import StopInfo
from petlib.ops import parse_number, parse_ref, run_until, wait_for_break, wait_for_text
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


def test_wait_for_break_flag_poll_catches_missed_event():
    """The STOPPED event can be lost to the connect-stop/resume race (demo-04
    flake). The hit flag in CHECKPOINT_LIST is durable — polling it must
    catch the halt even when no event is ever seen."""
    s, mon = _fake_session()
    ck_no = Checkpoint(number=3, hit=False, start=0x040D, end=0x040D, stop=True,
                       enabled=True, op=CP_EXEC, temporary=False, hit_count=0,
                       ignore_count=0, has_condition=False, memspace=0)
    ck_hit = Checkpoint(number=3, hit=True, start=0x040D, end=0x040D, stop=True,
                        enabled=True, op=CP_EXEC, temporary=False, hit_count=1,
                        ignore_count=0, has_condition=False, memspace=0)
    mon.checkpoint_list.side_effect = [[ck_no], [ck_hit]]
    mon.wait_for_stop.return_value = None      # the event was lost
    mon.registers.return_value = {"PC": 0x040D}
    out = wait_for_break(s, timeout=5)
    assert out["fired"] == "break" and out["checkpoint"] == 3


def _ck7(hit=False, hit_count=0):
    return Checkpoint(number=7, hit=hit, start=0x1000, end=0x1000, stop=True,
                      enabled=True, op=CP_EXEC, temporary=False,
                      hit_count=hit_count, ignore_count=0,
                      has_condition=False, memspace=0)


def test_run_until_count_uses_persistent_checkpoint():
    s, mon = _fake_session()
    mon.checkpoint_set.return_value = _ck7()
    mon.wait_for_stop.side_effect = [StopInfo(pc=0x1000, checkpoint=7)] * 2
    mon.registers.return_value = {"PC": 0x1000}
    out = run_until(s, 0x1000, timeout=5, count=2)
    assert out["registers"]["PC"] == 0x1000
    assert out["reached"] == 2 and out["count"] == 2
    mon.checkpoint_set.assert_called_once_with(0x1000, op=CP_EXEC, temporary=False)
    mon.checkpoint_delete.assert_called_once_with(7)
    assert mon.resume.call_count == 2          # exactly one resume per arrival


def test_run_until_timeout_cleans_up_checkpoint():
    s, mon = _fake_session()
    mon.checkpoint_set.return_value = _ck7()
    mon.wait_for_stop.return_value = None
    mon.checkpoint_list.return_value = [_ck7()]      # never hit
    out = run_until(s, 0x1000, timeout=0.3)
    assert out["registers"] is None and out["reached"] == 0 and out["count"] == 1
    mon.checkpoint_delete.assert_called_once_with(7)  # no leaked checkpoint


def test_session_labels_unreadable_file_returns_empty(tmp_path):
    from petlib.ops import session_labels
    s = Mock()
    s.labels = str(tmp_path / "gone.lbl")     # a path that does not exist
    assert session_labels(s) == {}


def test_pc_symbol_none_without_labels():
    from petlib.ops import pc_symbol
    assert pc_symbol({}, {"PC": 0x1234}) is None


def test_wait_for_mem_timeout_returns_last_value():
    from petlib.ops import wait_for_mem
    s = Mock()
    mon = Mock()
    s.monitor.return_value.__enter__ = Mock(return_value=mon)
    s.monitor.return_value.__exit__ = Mock(return_value=False)
    mon.memory_read.return_value = b"\x05"
    with patch("petlib.ops.time.sleep"):
        out = wait_for_mem(s, 0x8000, 0x2A, timeout=0.1)
    assert out["fired"] is None and out["last_value"] == 5


def test_find_bytes_single_and_pattern():
    from petlib.ops import find_bytes
    mon = Mock()
    mon.memory_read.return_value = b"\x00\x2a\x00\x2a\x2a"
    matches, truncated = find_bytes(mon, 0x8000, 5, b"\x2a")
    assert matches == [0x8001, 0x8003, 0x8004] and truncated is False
    matches, _ = find_bytes(mon, 0x8000, 5, b"\x2a\x2a")
    assert matches == [0x8003]
    mon.memory_read.assert_called_with(0x8000, 5)


def test_find_bytes_limit_truncates():
    from petlib.ops import find_bytes
    mon = Mock()
    mon.memory_read.return_value = b"\x00" * 10
    matches, truncated = find_bytes(mon, 0, 10, b"\x00", limit=3)
    assert len(matches) == 3 and truncated is True


def test_find_bytes_clamps_to_64k():
    from petlib.ops import find_bytes
    mon = Mock()
    mon.memory_read.return_value = b"\x01"
    find_bytes(mon, 0xFFFF, 0x100, b"\x01")
    mon.memory_read.assert_called_with(0xFFFF, 1)
