import json
import subprocess
import sys

import pytest

from petlib.session import Session, SessionError, sessions_dir


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))
    return tmp_path


def _write_record(name, pid, port=6502, model="pet4032"):
    d = sessions_dir()
    d.mkdir(parents=True, exist_ok=True)
    (d / f"{name}.json").write_text(
        json.dumps({"name": name, "pid": pid, "port": port, "model": model, "created": 0})
    )


def _live_pid():
    # a real process we control, standing in for xpet
    proc = subprocess.Popen([sys.executable, "-c", "import time; time.sleep(60)"])
    return proc


def test_attach_by_name(home):
    proc = _live_pid()
    try:
        _write_record("alpha", proc.pid)
        s = Session.attach("alpha")
        assert (s.name, s.pid, s.model) == ("alpha", proc.pid, "pet4032")
        assert s.profile.screen_cols == 40
    finally:
        proc.kill()


def test_attach_prunes_dead_and_errors(home):
    _write_record("ghost", 999999999)  # no such pid
    with pytest.raises(SessionError, match="pet session start"):
        Session.attach()
    assert not list(sessions_dir().glob("*.json"))  # dead record pruned


def test_attach_default_requires_exactly_one(home):
    p1, p2 = _live_pid(), _live_pid()
    try:
        _write_record("a", p1.pid)
        _write_record("b", p2.pid, port=6503)
        with pytest.raises(SessionError, match="--session"):
            Session.attach()
        assert Session.attach("b").port == 6503
    finally:
        p1.kill()
        p2.kill()


def test_list_all(home):
    proc = _live_pid()
    try:
        _write_record("only", proc.pid)
        assert [s.name for s in Session.list_all()] == ["only"]
    finally:
        proc.kill()


def test_launch_missing_binary_message(home, monkeypatch):
    monkeypatch.delenv("PET_TOOLS_XPET", raising=False)
    monkeypatch.setenv("PATH", "")
    with pytest.raises(SessionError, match="[Ii]nstall"):
        Session.launch(model="pet4032")


def test_launch_unknown_model(home):
    with pytest.raises(KeyError):
        Session.launch(model="amiga500")


def test_labels_path_persists(home):
    proc = _live_pid()
    try:
        _write_record("alpha", proc.pid)
        s = Session.attach("alpha")
        assert s.labels is None
        s.set_labels_path("/tmp/prog.lbl")
        again = Session.attach("alpha")
        # set_labels_path resolves; macOS resolves /tmp -> /private/tmp
        assert again.labels.endswith("/tmp/prog.lbl")
    finally:
        proc.kill()


def test_launch_disk8_args(home, tmp_path, monkeypatch):
    captured = {}

    class FakeProc:
        pid = 999_999_990  # never a live pid, so record pruning stays deterministic

        def terminate(self):
            pass

    def fake_popen(args, **kw):
        captured["args"] = args
        return FakeProc()

    monkeypatch.setattr("petlib.session.subprocess.Popen", fake_popen)
    monkeypatch.setattr("petlib.session.shutil.which", lambda n: "/usr/bin/xpet")

    class FakeMon:
        def __init__(self, *a, **k): ...
        def __enter__(self): return self
        def __exit__(self, *a): ...
        def connect(self, deadline=0): ...
        def ping(self): ...
        def resume(self): ...

    monkeypatch.setattr("petlib.session.MonitorClient", FakeMon)

    d80 = tmp_path / "big.d80"
    d80.write_bytes(b"x")
    Session.launch(model="pet8032", name="dsk", disk8=str(d80))
    args = captured["args"]
    assert "-8" in args and str(d80.resolve()) in args
    i = args.index("-drive8type")
    assert args[i + 1] == "8050"

    d64 = tmp_path / "small.d64"
    d64.write_bytes(b"x")
    Session.launch(model="pet4032", name="dsk2", disk8=str(d64))
    assert "-drive8type" not in captured["args"]      # 2031 is the default
    assert "-8" in captured["args"]
