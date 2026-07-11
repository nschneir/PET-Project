"""Session/daemon lifecycle units: circuit breaker + socket-path guard."""

import time

import pytest

from petlib.session import (RESPAWN_LIMIT, RESPAWN_WINDOW, Session,
                            SessionError, _default_socket_path)


def _s(tmp_path, monkeypatch, name="cb"):
    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))
    return Session(name=name, pid=1, port=1, model="pet4032")


def test_respawn_circuit_breaker_trips(tmp_path, monkeypatch):
    s = _s(tmp_path, monkeypatch)
    for _ in range(RESPAWN_LIMIT - 1):
        s._record_respawn_and_check()
    with pytest.raises(SessionError):
        s._record_respawn_and_check()


def test_respawn_breaker_ignores_old_crashes(tmp_path, monkeypatch):
    s = _s(tmp_path, monkeypatch, name="cb2")
    old = time.time() - (RESPAWN_WINDOW * 4)
    s._respawns_path().write_text(
        "\n".join(f"{old + i:.3f}" for i in range(RESPAWN_LIMIT - 1)))
    s._record_respawn_and_check()   # 5th overall, but the window has passed


def test_socket_path_prefers_sessions_dir(monkeypatch):
    monkeypatch.setenv("PET_TOOLS_HOME", "/tmp/pet-sockpath-test")
    p = _default_socket_path("snake")
    assert p == "/tmp/pet-sockpath-test/sessions/snake.sock"


def test_socket_path_length_guard(tmp_path, monkeypatch):
    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path / ("x" * 120)))
    p = _default_socket_path("verylongname")
    assert len(p.encode()) <= 100 and p.endswith(".sock")
