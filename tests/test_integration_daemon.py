"""Live daemon tests: the regressions that would have caught the original
transport bugs (2026-07-10 findings)."""

import json
import os
import shutil
import signal
import subprocess
import sys
import time
from pathlib import Path

import pytest

from petlib.build import build_asm
from petlib.session import Session, _pid_alive
from petlib.symbols import load_labels
from tests.test_integration_debug import HOT_LOOP
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


PET = Path(sys.executable).parent / "pet"


def _pet_json(*args):
    """Run the real pet CLI in a SEPARATE OS PROCESS — the original failure
    mode was per-process monitor connections."""
    out = subprocess.run([str(PET), "--json", *args],
                         capture_output=True, text=True, env=os.environ.copy())
    assert out.returncode == 0, f"pet {args}: {out.stderr}\n{out.stdout}"
    return json.loads(out.stdout)


def test_cross_process_stopped_state(session):
    """THE headline regression (findings §3.2 / DX Task-10 probe): a halt
    must survive across separate pet processes. Pre-daemon this free-ran
    (PC e0c3 -> e0c1)."""
    pc1 = _pet_json("step")["registers"]["PC"]
    pc2 = _pet_json("reg")["registers"]["PC"]
    pc3 = _pet_json("reg")["registers"]["PC"]
    assert pc1 == pc2 == pc3
    _pet_json("continue")


needs_cc65 = pytest.mark.skipif(
    shutil.which("ca65") is None and not os.environ.get("PET_TOOLS_CA65"),
    reason="cc65 not installed")


@needs_cc65
def test_idle_checkpoint_park_survives_inspection(session, tmp_path):
    """A checkpoint hit with NO client attached must flip the daemon to
    STOPPED (idle event pump) — otherwise the next inspection's release()
    would destroy the parked state."""
    src = tmp_path / "hot.s"
    src.write_text(HOT_LOOP)
    res = build_asm(src)
    labels = load_labels(res.labels)
    with session.monitor() as mon:
        try:
            mon.autostart(res.prg.resolve(), run=True)
        finally:
            mon.resume()
    time.sleep(3.0)
    with session.monitor() as mon:
        ck = mon.checkpoint_set(labels["mainloop"])
        mon.release()                    # running; the hit is imminent
    time.sleep(1.5)                      # the hit happens while idle
    with session.monitor() as mon:
        assert mon.registers()["PC"] == labels["mainloop"]
        mon.release()                    # must NOT resume a parked machine
    with session.monitor() as mon:       # still parked after inspection
        assert mon.registers()["PC"] == labels["mainloop"]
        mon.checkpoint_delete(ck.number)
        mon.resume()
