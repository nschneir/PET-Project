"""PetDaemon unit tests: dispatch, state machine, idle pump — all with a
mocked MonitorClient; the IPC leg is a real socketpair."""

import collections
import json
import os
import socket
import tempfile
import threading
import time
from unittest.mock import Mock

from petlib.daemon import RUNNING, STOPPED, PetDaemon
from petlib.daemon_client import DaemonMonitorClient
from petlib.monitor import StopInfo
from petlib.protocol import ResponseType


def _daemon(state=RUNNING):
    d = PetDaemon(Mock(), None, "t")
    d.state = state
    return d, d.mon


def _talk(d):
    a, b = socket.socketpair()
    t = threading.Thread(target=d._handle, args=(a,), daemon=True)
    t.start()
    f = b.makefile("rwb")
    hello = json.loads(f.readline())
    return b, f, t, hello


def _rpc(f, method, *args, **kwargs):
    f.write((json.dumps({"id": 1, "method": method, "args": list(args),
                         "kwargs": kwargs}) + "\n").encode())
    f.flush()
    return json.loads(f.readline())


def test_hello_greeting():
    d, _ = _daemon()
    b, f, t, hello = _talk(d)
    assert hello["hello"] == "pet-daemon" and hello["version"] == 1
    b.close(); t.join(timeout=2)


def test_dispatch_and_bytes_marshalling():
    d, mon = _daemon()
    mon.memory_read.return_value = b"\x2a"
    b, f, t, _ = _talk(d)
    resp = _rpc(f, "memory_read", 0x8000, 1)
    assert resp["ok"] == {"__bytes__": "Kg=="}
    mon.memory_read.assert_called_once_with(0x8000, 1)
    b.close(); t.join(timeout=2)


def test_unknown_method_rejected():
    d, _ = _daemon()
    b, f, t, _ = _talk(d)
    resp = _rpc(f, "os_system", "rm -rf /")
    assert resp["err"] == "ValueError"
    b.close(); t.join(timeout=2)


def test_step_sets_stopped_resume_sets_running():
    d, mon = _daemon()
    mon.step.return_value = {"PC": 0x0410}
    b, f, t, _ = _talk(d)
    _rpc(f, "step", 1)
    assert d.state == STOPPED
    _rpc(f, "resume")
    assert d.state == RUNNING
    mon.resume.assert_called_once()
    b.close(); t.join(timeout=2)


def test_release_running_resumes_stopped_noop():
    d, mon = _daemon(state=RUNNING)
    b, f, t, _ = _talk(d)
    _rpc(f, "release")
    mon.resume.assert_called_once()
    d.state = STOPPED
    _rpc(f, "release")
    mon.resume.assert_called_once()    # unchanged: parked stays parked
    b.close(); t.join(timeout=2)


def test_disconnect_restores_by_state():
    d, mon = _daemon(state=RUNNING)
    b, f, t, _ = _talk(d)
    # Close the makefile too: while it holds a socket reference the peer never
    # sees EOF. (Production clients are separate processes whose exit delivers
    # EOF; here client and daemon share one process.)
    f.close(); b.close(); t.join(timeout=2)
    mon.resume.assert_called_once()    # safety net resumed

    d2, mon2 = _daemon(state=STOPPED)
    b2, f2, t2, _ = _talk(d2)
    f2.close(); b2.close(); t2.join(timeout=2)
    mon2.resume.assert_not_called()    # parked machine left parked


def test_wait_for_stop_hit_sets_stopped():
    d, mon = _daemon()
    mon.wait_for_stop.return_value = StopInfo(pc=0x1000, checkpoint=3)
    b, f, t, _ = _talk(d)
    resp = _rpc(f, "wait_for_stop", 1.0)
    assert resp["ok"]["__stopinfo__"]["pc"] == 0x1000
    assert d.state == STOPPED
    b.close(); t.join(timeout=2)


def test_quit_ends_daemon_without_restore():
    d, mon = _daemon(state=RUNNING)
    mon.quit.return_value = None       # real MonitorClient.quit() returns None
    b, f, t, _ = _talk(d)
    resp = _rpc(f, "quit")
    assert "ok" in resp
    t.join(timeout=2)
    assert d._quitting is True
    mon.resume.assert_not_called()
    b.close()


def test_pump_flips_state_and_requeues():
    d, mon = _daemon(state=RUNNING)
    mon.events = collections.deque()
    ev = Mock(response_type=ResponseType.STOPPED)
    mon.poll_events.return_value = [ev]
    assert d._pump_vice_events() is True
    assert d.state == STOPPED and list(mon.events) == [ev]


def test_pump_reports_vice_death():
    d, mon = _daemon()
    mon.poll_events.side_effect = ConnectionError("gone")
    assert d._pump_vice_events() is False


def test_idle_wait_treats_closed_vice_socket_as_death():
    """If the VICE socket closes while the daemon idles (fileno -1), select
    used to raise ValueError and crash the daemon with a traceback. It must
    instead report VICE-gone so serve_forever shuts down cleanly."""
    d, mon = _daemon(state=RUNNING)
    a, b = socket.socketpair()
    d.listen = a
    mon._sock = b
    b.close()                          # VICE socket yanked out from under us
    assert d._idle_wait() is False     # returns cleanly (was ValueError: fd -1)
    a.close()


def test_handle_survives_client_gone_before_hello():
    """A command client that vanishes before reading the greeting used to
    crash the whole session daemon with BrokenPipeError (the hello send is
    outside _serve_client's try). _handle must swallow it and stay usable."""
    d, mon = _daemon(state=RUNNING)
    a, b = socket.socketpair()
    b.close()                     # peer gone before the daemon writes hello
    d._handle(a)                  # must NOT raise
    assert d._quitting is False   # session is fine; only that client is gone
    mon.resume.assert_called_once()  # RUNNING restored after the dropped client
    a.close()


def test_serve_forever_survives_bad_client_and_serves_next():
    """End to end: one client that connects and vanishes must not take down
    the daemon — the next command must still be greeted and served."""
    vice_a, vice_b = socket.socketpair()   # stand-in VICE sock; stays quiet
    mon = Mock()
    mon._sock = vice_a
    mon.ping.return_value = None
    sock_path = os.path.join(tempfile.mkdtemp(prefix="pet-sf-"), "d.sock")
    listen = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listen.bind(sock_path)
    listen.listen(1)
    d = PetDaemon(mon, listen, "t")
    th = threading.Thread(target=d.serve_forever, daemon=True)
    th.start()
    try:
        bad = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
        bad.connect(sock_path)
        bad.close()                # vanish before reading hello
        time.sleep(0.2)            # let the daemon accept + drop it
        good = DaemonMonitorClient(sock_path)   # reads hello in __init__
        good.ping()                # a real round-trip proves it still serves
        good.close()
        assert th.is_alive()       # the bad client did not kill the daemon
    finally:
        listen.close()
        vice_a.close()
        vice_b.close()
