"""Live daemon tests: the regressions that would have caught the original
transport bugs (2026-07-10 findings)."""

import json
import os
import signal
import time
from pathlib import Path

import pytest

from petlib.session import Session, _pid_alive
from tests.vice_helpers import wait_for_text

pytestmark = [
    pytest.mark.vice,
    pytest.mark.skipif(
        not (__import__("shutil").which("xpet") or os.environ.get("PET_TOOLS_XPET")),
        reason="xpet not installed",
    ),
]


@pytest.fixture
def session(tmp_path, monkeypatch):
    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))
    s = Session.launch(model="pet4032", name="dmntest", headless=True, warp=True)
    wait_for_text(s, "READY.")
    yield s
    s.stop()


def test_daemon_spawned_and_recorded(session, tmp_path):
    assert session.daemon_pid and _pid_alive(session.daemon_pid)
    assert session.socket and Path(session.socket).exists()
    rec = json.loads((tmp_path / "sessions" / "dmntest.json").read_text())
    assert rec["daemon_pid"] == session.daemon_pid
    assert rec["socket"] == session.socket


def test_stopped_state_survives_across_ipc_connections(session):
    """The original bug (findings §3.2): a step halt free-ran the moment the
    connection closed (PC e0c3 -> e0c1). Now the daemon holds it."""
    with session.monitor() as mon:
        pc1 = mon.step(1)["PC"]
    with session.monitor() as mon:      # a separate IPC connection
        regs = mon.registers()
        mon.release()                    # inspection must not un-park
    assert regs["PC"] == pc1
    with session.monitor() as mon:       # and again
        assert mon.registers()["PC"] == pc1
        mon.resume()                     # leave it running for teardown


def test_daemon_crash_respawns_with_warning(session, capsys):
    old = session.daemon_pid
    os.kill(old, signal.SIGKILL)
    time.sleep(0.3)
    with session.monitor() as mon:       # auto-respawn happens here
        mon.ping()
        mon.release()
    assert session.daemon_pid != old and _pid_alive(session.daemon_pid)
    assert "respawning" in capsys.readouterr().err
