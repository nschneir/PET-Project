"""MCP integration: stdio subprocess handshake + live-xpet flow in-memory."""

import json
import os
import shutil
import sys
from pathlib import Path

import anyio
import pytest
from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from mcp.shared.memory import (
    create_connected_server_and_client_session as client_session,
)


@pytest.fixture(autouse=True)
def home(tmp_path, monkeypatch):
    monkeypatch.setenv("PET_TOOLS_HOME", str(tmp_path))


def test_stdio_subprocess_handshake(tmp_path):
    """The installed pet-tools-mcp binary serves MCP over stdio.
    No emulator needed — pet_session_list works on an empty registry."""
    exe = Path(sys.executable).parent / "pet-tools-mcp"
    assert exe.exists(), "pet-tools-mcp entry point not installed"

    async def go():
        params = StdioServerParameters(
            command=str(exe), env={**os.environ, "PET_TOOLS_HOME": str(tmp_path)}
        )
        async with stdio_client(params) as (read, write):
            async with ClientSession(read, write) as cs:
                await cs.initialize()
                tools = await cs.list_tools()
                names = [t.name for t in tools.tools]
                assert "pet_screen_text" in names and "pet_build" in names
                r = await cs.call_tool("pet_session_list", {})
                assert json.loads(r.content[0].text) == {"sessions": []}

    anyio.run(go)


@pytest.mark.vice
@pytest.mark.skipif(
    not (shutil.which("xpet") or os.environ.get("PET_TOOLS_XPET")),
    reason="xpet not installed",
)
def test_live_flow_through_mcp():
    """Full loop via MCP tools: start session, wait for READY., type a BASIC
    program, wait for its output, read memory, stop."""
    from petlib.mcp_server import srv

    async def go():
        async with client_session(srv._mcp_server) as client:
            async def call(name, args):
                r = await client.call_tool(name, args)
                assert not r.isError, r.content[0].text
                return json.loads(r.content[0].text)

            out = await call("pet_session_start", {"model": "pet4032"})
            try:
                assert out["model"] == "pet4032"
                fired = await call("pet_wait_text", {"text": "READY.", "timeout": 45})
                assert fired["fired"] == "text"
                await call("pet_basic_type",
                           {"text": '10 print "HELLO VIA MCP"', "run": True})
                fired = await call("pet_wait_text",
                                   {"text": "HELLO VIA MCP", "timeout": 30})
                assert fired["fired"] == "text"
                screen = await call("pet_screen_text", {})
                assert "HELLO VIA MCP" in screen["text"]
                mem = await call("pet_mem_read", {"addr": "$8000", "length": 40})
                assert len(mem["hex"]) == 80
            finally:
                await call("pet_session_stop", {})

    anyio.run(go)
