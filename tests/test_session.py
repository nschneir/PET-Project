import json
import os
import signal
import subprocess
import sys
import time
from unittest.mock import Mock, patch

import pytest

from petlib.session import (
    Session,
    SessionError,
    _kill_proc,
    _pid_alive,
    sessions_dir,
)


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
    monkeypatch.setenv("PET_TOOLS_NO_DAEMON", "1")  # this test is about xpet args
    captured = {}

    class FakeProc:
        pid = 999_999_990  # never a live pid, so record pruning stays deterministic

        def poll(self):
            return None    # still running: the launch wait keeps waiting

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


def test_launch_retries_transient_monitor_failure(home, monkeypatch):
    """A first xpet whose monitor never answers should be retried on a fresh
    port, the failed proc killed (no orphan), and a second attempt succeed."""
    monkeypatch.setenv("PET_TOOLS_NO_DAEMON", "1")  # xpet retry logic, not the daemon
    monkeypatch.setenv("PET_TOOLS_LAUNCH_DEADLINE", "0.3")  # the wait is sliced now
    procs = []

    class FakeProc:
        _n = 0

        def __init__(self):
            FakeProc._n += 1
            self.pid = 900000 + FakeProc._n
            self.killed = False
            procs.append(self)

        def poll(self):
            return None                   # alive, just slow to open the monitor

        def terminate(self):
            self.killed = True

        def wait(self, timeout=None):
            return 0

        def kill(self):
            self.killed = True

    monkeypatch.setattr("petlib.session.subprocess.Popen", lambda *a, **k: FakeProc())
    monkeypatch.setattr("petlib.session.shutil.which", lambda n: "/usr/bin/xpet")

    calls = {"n": 0}

    class FakeMon:
        def __init__(self, *a, **k): ...
        def __enter__(self): return self
        def __exit__(self, *a): ...
        def connect(self, deadline=0):
            calls["n"] += 1
            if len(procs) == 1:           # the first xpet never answers
                raise TimeoutError("monitor slow")
        def ping(self): ...
        def resume(self): ...

    monkeypatch.setattr("petlib.session.MonitorClient", FakeMon)

    s = Session.launch(model="pet4032", name="retry")
    assert s.pid == procs[1].pid          # the second proc won
    assert procs[0].killed is True        # the first was cleaned up
    assert len(procs) == 2                # exactly one retry
    assert calls["n"] >= 2


def test_launch_exhausts_attempts_and_kills_all(home, monkeypatch):
    procs = []

    class FakeProc:
        def __init__(self):
            self.pid = 800000 + len(procs)
            self.killed = False
            procs.append(self)

        def poll(self):
            return None                   # alive throughout; just never answers

        def terminate(self):
            self.killed = True

        def wait(self, timeout=None):
            return 0

        def kill(self):
            self.killed = True

    monkeypatch.setenv("PET_TOOLS_LAUNCH_ATTEMPTS", "2")
    monkeypatch.setenv("PET_TOOLS_LAUNCH_DEADLINE", "0.3")  # the wait is sliced now
    monkeypatch.setattr("petlib.session.subprocess.Popen", lambda *a, **k: FakeProc())
    monkeypatch.setattr("petlib.session.shutil.which", lambda n: "/usr/bin/xpet")

    class FakeMon:
        def __init__(self, *a, **k): ...
        def __enter__(self): return self
        def __exit__(self, *a): ...
        def connect(self, deadline=0):
            raise ConnectionError("never answers")
        def ping(self): ...
        def resume(self): ...

    monkeypatch.setattr("petlib.session.MonitorClient", FakeMon)

    with pytest.raises(SessionError, match="never answered after 2"):
        Session.launch(model="pet4032", name="doomed")
    assert len(procs) == 2 and all(p.killed for p in procs)   # both cleaned up


# --- launch diagnostics ---------------------------------------------------
#
# The scripts below stand in for xpet. They write to STDOUT because that is
# where VICE puts its log by default (verified against VICE 3.10: a missing
# ROM set prints "PETMEM: Error - Couldn't load ROM `...'" on stdout and
# exits 255) — capturing only stderr would still discard everything.

# What VICE 3.10 actually prints when its PET ROMs are missing.
ROM_FAILURE_OUTPUT = """\
*** VICE Version 3.10 ***
Main: VICE system file search path: '/usr/share/vice'.
PETMEM: Error - Couldn't load ROM `basic-4.901465-23-20-21.bin'.
Error - Machine initialization failed."""


def _fake_xpet(tmp_path, name, body):
    """An executable standing in for xpet, running `body` as /bin/sh."""
    p = tmp_path / name
    p.write_text("#!/bin/sh\n" + body)
    p.chmod(0o755)
    return str(p)


def _dying_xpet(tmp_path, name, output, status=255):
    quoted = output.replace("\\", "\\\\").replace("'", "'\\''")
    return _fake_xpet(tmp_path, name, f"printf '%s\\n' '{quoted}'\nexit {status}\n")


class _WorkingMon:
    """A monitor that answers at once — isolates the process-watching logic."""

    def __init__(self, *a, **k): ...
    def __enter__(self): return self
    def __exit__(self, *a): ...
    def connect(self, deadline=0): ...
    def ping(self): ...
    def resume(self): ...


def test_launch_fails_fast_when_vice_exits(home, tmp_path, monkeypatch):
    """An xpet that dies at startup must be noticed immediately, not waited
    out. Before this, the connect loop ignored the child and burned the full
    deadline on every attempt (~40 s) before reporting only that the monitor
    never answered — the standard first-run experience on Debian/Ubuntu,
    where the packaged VICE has no ROMs."""
    monkeypatch.setenv("PET_TOOLS_NO_DAEMON", "1")
    monkeypatch.setenv("PET_TOOLS_LAUNCH_ATTEMPTS", "2")
    monkeypatch.setenv("PET_TOOLS_LAUNCH_DEADLINE", "20")
    monkeypatch.setenv(
        "PET_TOOLS_XPET", _dying_xpet(tmp_path, "xpet-dead", ROM_FAILURE_OUTPUT)
    )

    started = time.monotonic()
    with pytest.raises(SessionError) as excinfo:
        Session.launch(model="pet4032", name="dead")
    elapsed = time.monotonic() - started

    assert elapsed < 5.0, (
        f"launch took {elapsed:.1f}s; a dead xpet must not wait out the "
        f"2 x 20s deadline"
    )
    msg = str(excinfo.value)
    assert "255" in msg, f"exit status missing from: {msg}"
    assert "Couldn't load ROM" in msg, f"VICE's own output missing from: {msg}"


def test_launch_failure_hints_at_rom_install(home, tmp_path, monkeypatch):
    """A ROM-load failure is the Debian/Ubuntu trap, so it earns a pointer
    to the install docs."""
    monkeypatch.setenv("PET_TOOLS_NO_DAEMON", "1")
    monkeypatch.setenv("PET_TOOLS_LAUNCH_ATTEMPTS", "1")
    monkeypatch.setenv(
        "PET_TOOLS_XPET", _dying_xpet(tmp_path, "xpet-noroms", ROM_FAILURE_OUTPUT)
    )
    with pytest.raises(SessionError) as excinfo:
        Session.launch(model="pet4032", name="noroms")
    msg = str(excinfo.value)
    assert "README" in msg, f"no pointer to the install docs in: {msg}"
    assert "Debian" in msg or "apt" in msg, f"no Debian/Ubuntu context in: {msg}"


def test_launch_failure_without_rom_trouble_gets_no_rom_hint(
    home, tmp_path, monkeypatch
):
    """The hint must stay out of unrelated failures — a display problem is
    not a ROM problem, and guessing wrong sends users down a dead end."""
    monkeypatch.setenv("PET_TOOLS_NO_DAEMON", "1")
    monkeypatch.setenv("PET_TOOLS_LAUNCH_ATTEMPTS", "1")
    monkeypatch.setenv(
        "PET_TOOLS_XPET",
        _dying_xpet(tmp_path, "xpet-nodisplay",
                    "Gtk-WARNING **: cannot open display: \nError - "
                    "Machine initialization failed.", status=1),
    )
    with pytest.raises(SessionError) as excinfo:
        Session.launch(model="pet4032", name="nodisplay")
    msg = str(excinfo.value)
    assert "cannot open display" in msg, f"VICE's own output missing from: {msg}"
    assert "README" not in msg, f"ROM hint leaked into a display failure: {msg}"


def test_launch_succeeds_and_keeps_vice_output(home, tmp_path, monkeypatch):
    """Capturing VICE's output must not disturb a normal startup, and the
    captured log has to actually hold what VICE wrote."""
    monkeypatch.setenv("PET_TOOLS_NO_DAEMON", "1")
    monkeypatch.setenv(
        "PET_TOOLS_XPET",
        _fake_xpet(tmp_path, "xpet-alive",
                   'printf "*** VICE Version 3.10 ***\\n"\nexec sleep 30\n'),
    )
    monkeypatch.setattr("petlib.session.MonitorClient", _WorkingMon)

    s = Session.launch(model="pet4032", name="ok")
    try:
        assert s.is_alive()
        log = sessions_dir() / "ok.vice.log"
        assert log.exists(), "VICE's output was not captured anywhere"
        # The stub monitor answers instantly, so the child may not have
        # flushed yet; the point is that the output lands here at all rather
        # than in /dev/null.
        end = time.monotonic() + 5.0
        while "VICE Version" not in log.read_text() and time.monotonic() < end:
            time.sleep(0.05)
        assert "VICE Version" in log.read_text()
    finally:
        os.kill(s.pid, signal.SIGKILL)


def test_pid_alive_permission_error_means_alive(monkeypatch):
    def kill(pid, sig):
        raise PermissionError
    monkeypatch.setattr("petlib.session.os.kill", kill)
    assert _pid_alive(12345) is True


def test_kill_proc_escalates_to_sigkill():
    proc = Mock()
    proc.wait.side_effect = [subprocess.TimeoutExpired("x", 3), None]
    _kill_proc(proc)
    proc.terminate.assert_called_once()
    proc.kill.assert_called_once()


def test_kill_proc_survives_stubborn_process():
    proc = Mock()
    proc.wait.side_effect = subprocess.TimeoutExpired("x", 3)
    _kill_proc(proc)                      # both waits expire; must not raise
    proc.kill.assert_called_once()


def test_launch_rejects_duplicate_name(home, monkeypatch):
    monkeypatch.setenv("PET_TOOLS_XPET", "/usr/bin/xpet")  # skip the which() check
    existing = Mock()
    existing.name = "pet4032"
    with patch.object(Session, "_load_all", return_value=[existing]):
        with pytest.raises(SessionError, match="already running"):
            Session.launch(model="pet4032")


def test_attach_unknown_name_is_actionable(home):
    with pytest.raises(SessionError, match="pet session start"):
        Session.attach("nosuch")


def test_stop_cleans_up_dead_session(home):
    # a pid that is already dead (reaped) — stop() takes the not-alive path
    proc = subprocess.Popen([sys.executable, "-c", ""])
    proc.wait()
    dead = proc.pid
    sock = home / "sessions" / "z.sock"
    sock.parent.mkdir(parents=True, exist_ok=True)
    s = Session(name="z", pid=dead, port=6502, model="pet4032",
                daemon_pid=dead, socket=str(sock))
    s._record_path().write_text("{}")
    sock.write_text("")                   # a stale socket file to clean up
    s.stop()                              # must not raise
    assert not s._record_path().exists()
    assert not sock.exists()
