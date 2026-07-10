import json
import re
from pathlib import Path

from tests.doc_helpers import mentioned_commands, valid_mention_paths

README = Path("README.md")


def test_install_section_near_top():
    text = README.read_text()
    assert text.index("## Install") < text.index("## Quickstart")
    assert "brew install vice cc65" in text
    assert "apt install vice cc65" in text


def test_agents_section_covers_the_majors():
    text = README.read_text()
    idx = text.index("## Using with AI coding agents")
    section = text[idx:]
    for agent in ("Claude Code", "Codex", "Cursor", "Gemini", "Antigravity"):
        assert agent in section, f"agents section missing {agent}"
    for path in ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursor/mcp.json",
                 "config.toml", "mcp_config.json", ".gemini/settings.json"):
        assert path in section, f"agents section missing {path}"


def test_readme_mcp_json_snippet_parses():
    text = README.read_text()
    blocks = re.findall(r"```json\n(.*?)```", text, re.S)
    for block in blocks:
        json.loads(block)  # every fenced JSON snippet must be valid
    assert any("pet-tools-mcp" in b for b in blocks), \
        "agents section needs a fenced json mcpServers snippet using pet-tools-mcp"


def test_readme_pet_commands_exist():
    valid = valid_mention_paths()  # leaf commands plus bare group names
    unknown = {c for c in mentioned_commands(README.read_text()) if c not in valid}
    assert not unknown, f"README mentions nonexistent commands: {sorted(unknown)}"
