import pytest

from petlib.monitor import MonitorClient, MonitorError
from petlib.protocol import Command
from tests.fake_vice import FakeVice, resp_frame


def _client(fake: FakeVice) -> MonitorClient:
    c = MonitorClient(port=fake.port, timeout=2.0)
    c.connect(deadline=2.0)
    return c


def test_ping_roundtrip():
    fake = FakeVice({Command.PING: lambda body, rid: [resp_frame(0x81, 0, rid)]})
    with _client(fake) as c:
        c.ping()
    assert fake.received[0][0] == Command.PING


def test_memory_read():
    def handle(body, rid):
        return [resp_frame(0x01, 0, rid, bytes([4, 0]) + b"\x01\x02\x03\x04")]

    fake = FakeVice({Command.MEMORY_GET: handle})
    with _client(fake) as c:
        assert c.memory_read(0x8000, 4) == b"\x01\x02\x03\x04"
    # request body: side_effects=0, start=8000, end=8003, memspace=0, bank=0
    assert fake.received[0][1] == bytes([0, 0x00, 0x80, 0x03, 0x80, 0, 0, 0])


def test_events_are_queued_not_returned():
    def handle(body, rid):
        stopped = resp_frame(0x62, 0, 0xFFFFFFFF, b"\x01\x04")  # unsolicited
        return [stopped, resp_frame(0x81, 0, rid)]

    fake = FakeVice({Command.PING: handle})
    with _client(fake) as c:
        c.ping()
        assert len(c.events) == 1
        assert c.events[0].response_type == 0x62


def test_error_code_raises_monitor_error():
    fake = FakeVice({Command.MEMORY_GET: lambda b, rid: [resp_frame(0x01, 0x02, rid)]})
    with _client(fake) as c:
        with pytest.raises(MonitorError, match="INVALID_MEMSPACE"):
            c.memory_read(0x8000, 1)


def test_resume_sends_exit():
    fake = FakeVice({Command.EXIT: lambda b, rid: [resp_frame(0xAA, 0, rid)]})
    with _client(fake) as c:
        c.resume()
    assert fake.received[0][0] == Command.EXIT


def test_connect_refused_raises_after_deadline():
    c = MonitorClient(port=1, timeout=0.2)  # nothing listens on port 1
    with pytest.raises(ConnectionError):
        c.connect(deadline=0.5)
