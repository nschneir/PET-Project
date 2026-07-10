import json
from pathlib import Path
from unittest.mock import Mock, patch

from click.testing import CliRunner

from petlib.cli import main


def test_tokenize_default_output(tmp_path):
    src = tmp_path / "a.bas"
    src.write_text('10 print "hi"\n')
    with patch("petlib.cli.tokenize", return_value=tmp_path / "a.prg") as tok:
        r = CliRunner().invoke(main, ["--json", "basic", "tokenize", str(src)])
    assert r.exit_code == 0, r.output
    tok.assert_called_once_with(src, tmp_path / "a.prg", "4.0")
    assert json.loads(r.output)["prg"].endswith("a.prg")


def test_detokenize_listing(tmp_path):
    prg = tmp_path / "a.prg"
    prg.write_bytes(b"\x01\x04")
    with patch("petlib.cli.detokenize", return_value='10 print "hi"\n'):
        r = CliRunner().invoke(main, ["basic", "detokenize", str(prg)])
    assert r.exit_code == 0
    assert 'print "hi"' in r.output


def _fake_attached():
    fake = Mock()
    fake.name, fake.model = "pet4032", "pet4032"
    mon = Mock()
    fake.monitor.return_value.__enter__ = Mock(return_value=mon)
    fake.monitor.return_value.__exit__ = Mock(return_value=False)
    return fake, mon


def test_type_feeds_keyboard_and_run(tmp_path):
    src = tmp_path / "a.bas"
    src.write_text('10 print "HI"\n')
    fake, mon = _fake_attached()
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["basic", "type", str(src), "--run"])
    assert r.exit_code == 0, r.output
    fed = b"".join(c.args[0] for c in mon.keyboard_feed.call_args_list)
    assert fed == b'10 PRINT "HI"\rRUN\r'
    mon.resume.assert_called_once()


def test_key_type_feeds_text_directly():
    fake, mon = _fake_attached()
    with patch("petlib.cli.Session") as S:
        S.attach.return_value = fake
        r = CliRunner().invoke(main, ["key", "type", "50\n"])
    assert r.exit_code == 0, r.output
    mon.keyboard_feed.assert_called_once_with(b"50\r")
    mon.resume.assert_called_once()
