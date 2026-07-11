"""DaemonMonitorClient round-trips against a real PetDaemon (mocked
MonitorClient) over a real unix socket."""

import socket
import tempfile
import threading
from pathlib import Path
from unittest.mock import Mock

import pytest

from petlib.daemon import STOPPED, PetDaemon
from petlib.daemon_client import DaemonMonitorClient
from petlib.monitor import MonitorClient, StopInfo
from petlib.protocol import CP_EXEC, Checkpoint


@pytest.fixture
def served():
    """(client, mock_mon, daemon) with the daemon handling one connection."""
    mon = Mock()
    sock_path = str(Path(tempfile.mkdtemp(prefix="pet-dc-")) / "d.sock")
    listen = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listen.bind(sock_path)
    listen.listen(1)
    d = PetDaemon(mon, listen, "t")

    def run():
        client, _ = listen.accept()
        d._handle(client)

    t = threading.Thread(target=run, daemon=True)
    t.start()
    c = DaemonMonitorClient(sock_path)
    yield c, mon, d
    c.close()
    t.join(timeout=2)
    listen.close()


def test_memory_read_bytes_round_trip(served):
    c, mon, _ = served
    mon.memory_read.return_value = b"\x2a\x00"
    assert c.memory_read(0x8000, 2) == b"\x2a\x00"
    mon.memory_read.assert_called_once_with(0x8000, 2)


def test_memory_write_sends_bytes(served):
    c, mon, _ = served
    mon.memory_write.return_value = None    # real MonitorClient returns None
    c.memory_write(0x8000, b"\x01\x02")
    mon.memory_write.assert_called_once_with(0x8000, b"\x01\x02")


def test_checkpoint_set_round_trip(served):
    c, mon, _ = served
    ck = Checkpoint(number=4, hit=False, start=0x040F, end=0x040F, stop=True,
                    enabled=True, op=CP_EXEC, temporary=False, hit_count=0,
                    ignore_count=0, has_condition=False, memspace=0)
    mon.checkpoint_set.return_value = ck
    out = c.checkpoint_set(0x040F, op=CP_EXEC, temporary=False)
    assert out == ck and isinstance(out, Checkpoint)
    mon.checkpoint_set.assert_called_once_with(0x040F, None, op=CP_EXEC,
                                               temporary=False)


def test_exception_maps_to_local_type(served):
    c, mon, _ = served
    mon.registers.side_effect = TimeoutError("no response to REGISTERS_GET")
    with pytest.raises(TimeoutError):
        c.registers()


def test_wait_for_stop_round_trip_sets_stopped(served):
    c, mon, d = served
    mon.wait_for_stop.return_value = StopInfo(pc=0x1000, checkpoint=7)
    assert c.wait_for_stop(2.0) == StopInfo(pc=0x1000, checkpoint=7)
    assert d.state == STOPPED


def test_autostart_sends_str_path(served):
    c, mon, _ = served
    mon.autostart.return_value = None       # real MonitorClient returns None
    c.autostart(Path("/tmp/x.prg"), run=True)
    mon.autostart.assert_called_once_with("/tmp/x.prg", run=True)


def test_release_restores_running(served):
    c, mon, _ = served
    c.release()
    mon.resume.assert_called_once()


def test_not_a_daemon_socket_raises(tmp_path_factory):
    d = tempfile.mkdtemp(prefix="pet-dc-")
    path = str(Path(d) / "bogus.sock")
    listen = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listen.bind(path)
    listen.listen(1)

    def run():
        cl, _ = listen.accept()
        cl.sendall(b'{"nope": 1}\n')
        cl.close()

    t = threading.Thread(target=run, daemon=True)
    t.start()
    with pytest.raises(ConnectionError):
        DaemonMonitorClient(path)
    t.join(timeout=2)
    listen.close()


def test_close_delivers_eof_so_next_client_is_served_promptly():
    """THE hang regression: close() must close the makefile too, or the fd
    stays open, the daemon never sees EOF, and the NEXT client's hello read
    times out while the old client object is still referenced — exactly the
    wait_for_text loop pattern (`with session.monitor() as mon:` per poll)."""
    vice_a, vice_b = socket.socketpair()   # quiet stand-in for the VICE sock
    mon = Mock()
    mon._sock = vice_a
    mon.ping.return_value = None
    sock_path = str(Path(tempfile.mkdtemp(prefix="pet-dc-")) / "d.sock")
    listen = socket.socket(socket.AF_UNIX, socket.SOCK_STREAM)
    listen.bind(sock_path)
    listen.listen(1)
    d = PetDaemon(mon, listen, "t")
    th = threading.Thread(target=d.serve_forever, daemon=True)
    th.start()
    try:
        c1 = DaemonMonitorClient(sock_path, timeout=2.0)
        c1.ping()
        c1.close()
        # c1 stays referenced (like `mon` after a with-block) — only a real
        # fd close can deliver EOF. The next client must be greeted fast.
        c2 = DaemonMonitorClient(sock_path, timeout=2.0)
        c2.ping()
        c2.close()
        assert c1 is not None              # keep c1 alive to the very end
    finally:
        listen.close()
        vice_a.close()
        vice_b.close()


def test_direct_monitorclient_release_aliases_resume():
    m = MonitorClient.__new__(MonitorClient)
    calls = []
    m.resume = lambda: calls.append(1)
    m.release()
    assert calls == [1]
