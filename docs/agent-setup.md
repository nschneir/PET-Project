# Using PET Project with AI coding agents

<!-- Keep this intro in sync with the README's "Using with AI coding agents" section -->

This toolset is built to be driven by an AI agent. Debugging state persists
across commands: when the agent halts the machine at a breakpoint, it stays
halted while the agent inspects memory, registers, and screen in separate tool
calls. There are two ways an agent can use it — pick either or both:

- **The CLI** — every `pet` command takes `--json`. Works with *any* agent
  that can run shell commands; nothing to configure.
- **The MCP server** — `pet-tools-mcp` exposes the same operations as MCP
  tools over stdio. CLI and MCP share the same sessions, so they are
  interchangeable.

Either way, the agent should read
[`skills/pet-development/SKILL.md`](../skills/pet-development/SKILL.md) (the PET
workflows and pitfalls) before starting — the per-agent steps below make that
happen automatically. The command reference is in [`cli.md`](cli.md).

Everything here works the same on **macOS and Linux**: the commands are plain
POSIX, and the CLI config files shown below (`~/.codex/config.toml`,
`~/.cursor/mcp.json`, `~/.gemini/settings.json`) live in your home directory on
both. Installing the prerequisites is the step that differs, and the
[README's Install section](../README.md#install) covers both macOS (Homebrew)
and Debian/Ubuntu (apt) — note that Debian/Ubuntu need several extra steps
(enable `contrib`, install the PET ROMs by hand, use a venv). Every MCP config
here assumes `pet-tools-mcp` resolves from your `PATH`, so on Linux activate
the venv you installed into (or use `pipx`) before starting your agent.

The MCP config used by several agents below is this one block:

```json
{
  "mcpServers": {
    "pet-tools": { "command": "pet-tools-mcp" }
  }
}
```

Setup was verified against each agent's docs in **July 2026**; if something
has moved, check the agent's current MCP documentation.

## Any agent with a shell (simplest — works everywhere)

1. Install (see the [README](../README.md#install)) — that's the whole setup.
2. Start your task prompt with: *"Read docs/cli.md and
   skills/pet-development/SKILL.md, then …"*

## Claude Code

1. From the repo root, install the skills so Claude discovers them
   automatically:

   ```
   mkdir -p .claude/skills && cp -R skills/* .claude/skills/
   ```

2. (Optional) Add the MCP server: `claude mcp add pet-tools -- pet-tools-mcp`
3. Ask for what you want — e.g. paste a prompt from [`demos/`](../demos/).

No `CLAUDE.md` edits are needed: installed skills load on demand, and the MCP
tools describe themselves.

## OpenAI Codex

1. Add the MCP server: `codex mcp add pet-tools -- pet-tools-mcp`
   (or add `[mcp_servers.pet_tools]` with `command = "pet-tools-mcp"` to
   `~/.codex/config.toml`).
2. Codex has no skills mechanism, so tell it where the docs are: add one line
   to the repo's `AGENTS.md` — *"For Commodore PET work, first read
   skills/pet-development/SKILL.md and docs/cli.md."*
3. Paste a prompt from [`demos/`](../demos/).

## Cursor

1. Create `.cursor/mcp.json` in the repo (or `~/.cursor/mcp.json` globally)
   containing the JSON block above.
2. Create a rule (`.cursor/rules/pet.mdc`) — or a plain `AGENTS.md` — with the
   same one-liner: *"For Commodore PET work, first read
   skills/pet-development/SKILL.md and docs/cli.md."*
3. Paste a prompt from [`demos/`](../demos/).

## Gemini CLI

1. Add the JSON block above to `.gemini/settings.json` in the repo (or
   `~/.gemini/settings.json` globally).
2. Add the same read-the-skill one-liner to `GEMINI.md`.
3. Paste a prompt from [`demos/`](../demos/).

## Google Antigravity

1. Open the MCP store → **Manage MCP Servers** → **View raw config** and add
   the JSON block above (the file is `~/.gemini/config/mcp_config.json`).
2. Add the read-the-skill one-liner to `AGENTS.md`.
3. Paste a prompt from [`demos/`](../demos/).
