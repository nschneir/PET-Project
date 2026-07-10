import json
from unittest.mock import Mock, patch

from click.testing import CliRunner

from petlib.cli import main, parse_number


def test_parse_number():
    assert parse_number("$8000") == 0x8000
    assert parse_number("0x8000") == 0x8000
    assert parse_number("1024") == 1024


def _patched(mon):
    fake = Mock()
    fake.name, fake.model = "pet4032", "pet4032"
    fake.monitor.return_value.__enter__ = Mock(return_value=mon)
    fake.monitor.return_value.__exit__ = Mock(return_value=False)
    p = patch("petlib.cli.Session")
    return fake, p


def test_screen_text():
    mon = Mock()
    fake, p = _patched(mon)
    with p as S, patch("petlib.cli.read_screen_text", return_value="READY.") as rst:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "screen"])
    assert r.exit_code == 0, r.output
    assert json.loads(r.output)["text"] == "READY."
    mon.resume.assert_called_once()


def test_mem_read_hexdump():
    mon = Mock()
    mon.memory_read.return_value = bytes(range(16))
    fake, p = _patched(mon)
    with p as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["mem", "read", "$8000", "16"])
    assert r.exit_code == 0
    assert r.output.startswith("8000: 00 01 02")
    mon.memory_read.assert_called_once_with(0x8000, 16)
    mon.resume.assert_called_once()


def test_mem_write():
    mon = Mock()
    fake, p = _patched(mon)
    with p as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["mem", "write", "$8000", "0x01", "2", "$FF"])
    assert r.exit_code == 0
    mon.memory_write.assert_called_once_with(0x8000, bytes([1, 2, 0xFF]))
    mon.resume.assert_called_once()


def test_reg_get_and_set():
    mon = Mock()
    mon.registers.return_value = {"PC": 0x0401, "A": 0x2A}
    fake, p = _patched(mon)
    with p as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "reg"])
        assert json.loads(r.output)["registers"]["PC"] == 0x0401
        r2 = CliRunner().invoke(main, ["reg", "set", "PC", "$2000"])
    assert r2.exit_code == 0
    mon.set_register.assert_called_once_with("PC", 0x2000)


def _mem_fake(labels_path=None):
    s = Mock()
    s.labels = labels_path
    mon = Mock()
    s.monitor.return_value.__enter__ = Mock(return_value=mon)
    s.monitor.return_value.__exit__ = Mock(return_value=False)
    return s, mon


def test_mem_read_accepts_symbol(tmp_path):
    lbl = tmp_path / "t.lbl"
    lbl.write_text("al 0006BC .SCORE\n")
    fake, mon = _mem_fake(str(lbl))
    mon.memory_read.return_value = b"\x2a"
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "mem", "read", "SCORE", "1"])
    assert r.exit_code == 0, r.output
    mon.memory_read.assert_called_once_with(0x06BC, 1)
    assert json.loads(r.output)["hex"] == "2a"


def test_mem_write_accepts_symbol(tmp_path):
    lbl = tmp_path / "t.lbl"
    lbl.write_text("al 0006BA .STEPMODE\n")
    fake, mon = _mem_fake(str(lbl))
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "mem", "write", "STEPMODE", "0"])
    assert r.exit_code == 0, r.output
    mon.memory_write.assert_called_once_with(0x06BA, b"\x00")


def test_mem_read_unknown_symbol_fails():
    fake, _ = _mem_fake(None)
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["--json", "mem", "read", "NOSUCH", "1"])
    assert r.exit_code == 1
    assert "NOSUCH" in json.loads(r.output)["error"]
