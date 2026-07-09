"""MCP server exposing pet-tools to MCP-native AI clients (spec §3.3).

Thin wrappers over the same petlib operations the CLI uses; CLI and MCP are
interchangeable against the same session registry. Tools return the same
structured data as the CLI's --json. Raised petlib exceptions surface as MCP
tool errors with their actionable messages intact.
"""

from __future__ import annotations

from mcp.server.fastmcp import FastMCP

from .session import Session

srv = FastMCP("pet-tools")


def _attach(session: str | None = None) -> Session:
    return Session.attach(session)


@srv.tool()
def pet_session_list() -> dict:
    """List running emulated PET sessions (name, model, pid, monitor port)."""
    return {"sessions": [
        {"name": s.name, "model": s.model, "pid": s.pid, "port": s.port}
        for s in Session.list_all()
    ]}


def main() -> None:
    srv.run()


if __name__ == "__main__":
    main()
