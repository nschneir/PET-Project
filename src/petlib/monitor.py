"""Socket client for the VICE binary monitor.

Connection-behavior contract (see spec §5 'stopped-state discipline'):
processing any monitor command leaves the emulated machine STOPPED. Callers
that want the machine running afterwards must call resume().
"""

from __future__ import annotations

import collections
import itertools
import socket
import struct
import time

from .protocol import (
    Command,
    ErrorCode,
    FrameDecoder,
    Response,
    encode_command,
    memory_get_body,
    memory_set_body,
    parse_display_get,
    parse_memory_get,
    parse_palette_get,
    parse_registers_available,
    parse_registers_get,
    registers_set_body,
)


class MonitorError(Exception):
    def __init__(self, command: int, error_code: int):
        try:
            name = ErrorCode(error_code).name
        except ValueError:
            name = f"{error_code:#04x}"
        super().__init__(f"VICE monitor error {name} for command {Command(command).name}")
        self.error_code = error_code


class MonitorClient:
    def __init__(self, host: str = "127.0.0.1", port: int = 6502, timeout: float = 5.0):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.events: collections.deque[Response] = collections.deque(maxlen=256)
        self._sock: socket.socket | None = None
        self._decoder = FrameDecoder()
        self._ids = itertools.count(1)
        self._pending: list[Response] = []

    def connect(self, deadline: float = 15.0) -> None:
        end = time.monotonic() + deadline
        last_err: Exception | None = None
        while time.monotonic() < end:
            try:
                self._sock = socket.create_connection(
                    (self.host, self.port), timeout=self.timeout
                )
                return
            except OSError as e:
                last_err = e
                time.sleep(0.1)
        raise ConnectionError(
            f"could not connect to VICE monitor at {self.host}:{self.port}: {last_err}"
        )

    def close(self) -> None:
        if self._sock is not None:
            self._sock.close()
            self._sock = None

    def __enter__(self) -> "MonitorClient":
        return self

    def __exit__(self, *exc) -> None:
        self.close()

    def request(self, command: int, body: bytes = b"") -> Response:
        assert self._sock is not None, "not connected"
        rid = next(self._ids)
        self._sock.sendall(encode_command(command, body, request_id=rid))
        deadline = time.monotonic() + self.timeout
        while True:
            for resp in self._pending:
                if resp.request_id == rid:
                    self._pending.remove(resp)
                    if resp.error_code != ErrorCode.OK:
                        raise MonitorError(command, resp.error_code)
                    return resp
            if time.monotonic() > deadline:
                raise TimeoutError(f"no response to {Command(command).name}")
            data = self._sock.recv(65536)
            if not data:
                raise ConnectionError("VICE closed the monitor connection")
            for resp in self._decoder.feed(data):
                if resp.is_event:
                    self.events.append(resp)
                else:
                    self._pending.append(resp)

    # --- high-level operations -------------------------------------------

    def ping(self) -> None:
        self.request(Command.PING)

    def memory_read(
        self, start: int, length: int, *, memspace: int = 0, bank: int = 0
    ) -> bytes:
        body = memory_get_body(start, start + length - 1, memspace, bank)
        return parse_memory_get(self.request(Command.MEMORY_GET, body).body)

    def memory_write(
        self, start: int, data: bytes, *, memspace: int = 0, bank: int = 0
    ) -> None:
        self.request(Command.MEMORY_SET, memory_set_body(start, data, memspace, bank))

    def resume(self) -> None:
        self.request(Command.EXIT)

    def _register_map(self) -> dict[int, str]:
        if not hasattr(self, "_regmap"):
            body = self.request(Command.REGISTERS_AVAILABLE, b"\x00").body
            self._regmap = parse_registers_available(body)
        return self._regmap

    def registers(self) -> dict[str, int]:
        regmap = self._register_map()
        raw = parse_registers_get(self.request(Command.REGISTERS_GET, b"\x00").body)
        return {regmap[i].upper(): v for i, v in raw.items() if i in regmap}

    def set_register(self, name: str, value: int) -> None:
        regmap = self._register_map()
        by_name = {n.upper(): i for i, n in regmap.items()}
        reg_id = by_name[name.upper()]  # KeyError on unknown name is the contract
        self.request(Command.REGISTERS_SET, registers_set_body({reg_id: value}))

    def reset(self, hard: bool = False) -> None:
        self.request(Command.RESET, b"\x01" if hard else b"\x00")

    def keyboard_feed(self, petscii: bytes) -> None:
        for i in range(0, len(petscii), 200):
            chunk = petscii[i : i + 200]
            self.request(Command.KEYBOARD_FEED, bytes([len(chunk)]) + chunk)

    def display(self) -> tuple[int, int, bytes]:
        # body: use_vic flag (ignored for PET), format 0 = indexed 8bpp
        return parse_display_get(self.request(Command.DISPLAY_GET, b"\x00\x00").body)

    def palette(self) -> list[tuple[int, int, int]]:
        return parse_palette_get(self.request(Command.PALETTE_GET, b"\x00").body)

    def vice_info(self) -> str:
        body = self.request(Command.VICE_INFO).body
        n = body[0]
        return ".".join(str(b) for b in body[1 : 1 + n]).rstrip(".0") or "0"

    def quit(self) -> None:
        try:
            self.request(Command.QUIT)
        except (ConnectionError, TimeoutError, OSError):
            pass  # VICE may exit before replying

    def autostart(self, path, run: bool = True) -> None:
        """Load-and-optionally-RUN a program file via VICE's autostart.

        VICE mounts the file as a virtual drive and types LOAD/RUN itself;
        pass an absolute path. Loading takes a few emulated seconds.
        """
        name = str(path).encode()
        body = struct.pack("<BHB", int(run), 0, len(name)) + name
        self.request(Command.AUTOSTART, body)
