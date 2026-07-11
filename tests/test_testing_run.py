from pathlib import Path
from unittest.mock import Mock, patch

import pytest

from petlib.testing import TestError, run_test


def _fake_session():
    s = Mock()
    s.profile.basic_version = "4.0"
    s.profile.basic_start = 0x0401
    mon = Mock()
    s.monitor.return_value.__enter__ = Mock(return_value=mon)
    s.monitor.return_value.__exit__ = Mock(return_value=False)
    return s, mon


def _spec(**kw):
    base = {"name": "t", "machine": "pet4032", "timeout": 2,
            "autorun": True, "steps": []}
    base.update(kw)
    return base


def test_happy_path_key_wait_assert(tmp_path):
    s, mon = _fake_session()
    launch = Mock(return_value=s)
    mon.registers.return_value = {"PC": 0xC500}
    screens = ["READY.", "READY.", "HELLO", "HELLO", "HELLO"]
    spec = _spec(steps=[
        {"key": "RUN\n"},
        {"wait": {"text": "HELLO"}},
        {"assert": {"reg": "pc", "in_range": ["$C000", "$E000"]}},
    ])
    with patch("petlib.testing.read_screen_text", side_effect=screens):
        result = run_test(spec, launch=launch)
    assert result.passed is True
    assert [st.ok for st in result.steps] == [True, True, True]
    launch.assert_called_once_with(model="pet4032", name=result.session_name,
                                   headless=True, warp=True)
    mon.keyboard_feed.assert_called_once_with(b"RUN\r")
    s.stop.assert_called_once()


def test_fail_fast_captures_screen():
    s, mon = _fake_session()
    launch = Mock(return_value=s)
    # constant screen: boot sees READY. immediately; the failing wait spins
    # (sleep patched to a no-op) without exhausting a side_effect list
    spec = _spec(steps=[
        {"wait": {"text": "NEVER", "timeout": 0.5}},
        {"key": "RUN\n"},          # must not execute
    ])
    with patch("petlib.testing.read_screen_text", return_value="READY.\nNOPE"), \
         patch("petlib.testing.time.sleep"):
        result = run_test(spec, launch=launch)
    assert result.passed is False
    assert len(result.steps) == 1 and result.steps[0].ok is False
    assert "NOPE" in result.screen
    mon.keyboard_feed.assert_not_called()
    s.stop.assert_called_once()


def test_assert_mem_equals_text():
    s, mon = _fake_session()
    launch = Mock(return_value=s)
    # screen codes for "HI" are 8, 9
    mon.memory_read.return_value = bytes([8, 9])
    spec = _spec(steps=[{"assert": {"mem": "$8000", "equals_text": "HI"}}])
    with patch("petlib.testing.read_screen_text", return_value="READY."):
        result = run_test(spec, launch=launch)
    assert result.passed is True
    mon.memory_read.assert_called_with(0x8000, 2)


def test_program_bas_tokenized_and_autostarted(tmp_path):
    prog = tmp_path / "p.bas"
    prog.write_text('10 print "hi"\n')
    s, mon = _fake_session()
    launch = Mock(return_value=s)
    spec = _spec(program=str(prog))
    with patch("petlib.testing.read_screen_text", return_value="READY."), \
         patch("petlib.testing.tokenize", return_value=tmp_path / "p.prg") as tok:
        result = run_test(spec, launch=launch)
    assert result.passed is True
    tok.assert_called_once_with(prog, prog.with_suffix(".prg"), "4.0")
    mon.autostart.assert_called_once_with((tmp_path / "p.prg").resolve(), run=True)


def test_autorun_false_waits_for_load(tmp_path):
    prog = tmp_path / "p.prg"
    prog.write_bytes(b"\x01\x04")
    s, mon = _fake_session()
    launch = Mock(return_value=s)
    screens = ["READY.",                                  # boot
               "LOAD\"*\",8\n\nSEARCHING",                # loading...
               "LOAD\"*\",8\n\nSEARCHING\nLOADING\nREADY.",  # loaded
               "DONE", "DONE"]
    spec = _spec(program=str(prog), autorun=False,
                 steps=[{"wait": {"text": "DONE"}}])
    with patch("petlib.testing.read_screen_text", side_effect=screens), \
         patch("petlib.testing.time.sleep"):
        result = run_test(spec, launch=launch)
    assert result.passed is True
    mon.autostart.assert_called_once_with(prog.resolve(), run=False)


def test_boot_timeout_is_error():
    s, mon = _fake_session()
    launch = Mock(return_value=s)
    with patch("petlib.testing.read_screen_text", return_value="GARBAGE"), \
         patch("petlib.testing.time.sleep"), \
         patch("petlib.testing.time.monotonic", side_effect=[i * 10.0 for i in range(100)]):
        with pytest.raises(TestError, match="READY"):
            run_test(_spec(), launch=launch)
    s.stop.assert_called_once()


def test_wait_mem_polls_until_value():
    s, mon = _fake_session()
    launch = Mock(return_value=s)
    mon.memory_read.side_effect = [b"\x00", b"\x00", b"\x2a"]
    spec = _spec(steps=[{"wait": {"mem": "$8000", "equals": "$2a"}}])
    with patch("petlib.testing.read_screen_text", return_value="READY."), \
         patch("petlib.testing.time.sleep"):
        result = run_test(spec, launch=launch)
    assert result.passed is True
    assert mon.memory_read.call_count == 3


def test_wait_mem_timeout_reports_last_value():
    s, mon = _fake_session()
    launch = Mock(return_value=s)
    mon.memory_read.return_value = b"\x07"
    spec = _spec(steps=[{"wait": {"mem": "$8000", "equals": "$2a", "timeout": 0.2}}])
    with patch("petlib.testing.read_screen_text", return_value="READY."), \
         patch("petlib.testing.time.sleep"):
        result = run_test(spec, launch=launch)
    assert result.passed is False
    assert "was 7" in result.steps[0].detail and "wanted 42" in result.steps[0].detail


def test_assert_reg_unknown_register_fails_cleanly():
    s, mon = _fake_session()
    launch = Mock(return_value=s)
    mon.registers.return_value = {"PC": 0x1234, "A": 0}
    spec = _spec(steps=[{"assert": {"reg": "q", "equals": 1}}])
    with patch("petlib.testing.read_screen_text", return_value="READY."):
        result = run_test(spec, launch=launch)
    assert result.passed is False and "no register" in result.steps[0].detail


def test_assert_reg_in_range_fail_branch():
    s, mon = _fake_session()
    launch = Mock(return_value=s)
    mon.registers.return_value = {"PC": 0xC500}
    spec = _spec(steps=[{"assert": {"reg": "pc", "in_range": ["$0400", "$0500"]}}])
    with patch("petlib.testing.read_screen_text", return_value="READY."):
        result = run_test(spec, launch=launch)
    assert result.passed is False and "not in" in result.steps[0].detail


def test_autorun_false_load_never_finishes():
    s, _ = _fake_session()
    launch = Mock(return_value=s)
    spec = _spec(autorun=False, timeout=0.2, program="whatever.prg", steps=[])
    # First _wait_screen (READY gate) passes; second (load gate) never does.
    # Patching _wait_screen directly avoids the 45s/15s real-time deadlines.
    with patch("petlib.testing._wait_screen",
               side_effect=[(True, "READY."), (False, "LOADING")]), \
         patch("petlib.testing._prepare", return_value=Path("x.prg")), \
         pytest.raises(TestError, match="never finished loading"):
        run_test(spec, launch=launch)
