import json
import re
from pathlib import Path

from tests.doc_helpers import (
    BOOT_FREE,
    code_blocks,
    mentioned_commands,
    valid_mention_paths,
)

README = Path("README.md")
AGENT_SETUP = Path("docs/agent-setup.md")


def test_install_section_near_top():
    text = README.read_text()
    assert text.index("## Install") < text.index("## Quickstart")
    assert "brew install vice cc65" in text
    assert "apt install vice cc65" in text


def test_readme_agents_section_links_to_the_setup_guide():
    """The README keeps the two-route pitch; the per-agent steps live in
    docs/agent-setup.md, and the section must point at it."""
    text = README.read_text()
    idx = text.index("## Using with AI coding agents")
    section = text[idx:text.index("\n## ", idx + 1)]
    assert "docs/agent-setup.md" in section, \
        "agents section must link to docs/agent-setup.md"
    assert AGENT_SETUP.exists(), "docs/agent-setup.md is missing"
    for route in ("--json", "pet-tools-mcp"):
        assert route in section, f"agents section missing the {route} route"


def test_agent_setup_guide_covers_the_majors():
    guide = AGENT_SETUP.read_text()
    for agent in ("Claude Code", "Codex", "Cursor", "Gemini", "Antigravity"):
        assert agent in guide, f"agent-setup.md missing {agent}"
    for path in ("CLAUDE.md", "AGENTS.md", "GEMINI.md", ".cursor/mcp.json",
                 "config.toml", "mcp_config.json", ".gemini/settings.json",
                 "skills/pet-development/SKILL.md"):
        assert path in guide, f"agent-setup.md missing {path}"


def test_agent_setup_guide_works_on_macos_and_linux():
    """The guide is the only per-agent setup doc, so it must not read as
    macOS-only: it names both platforms and stays off macOS-only tooling."""
    guide = AGENT_SETUP.read_text()
    assert "macOS" in guide and "Linux" in guide, \
        "agent-setup.md must state it applies to macOS and Linux"
    for macos_only in ("brew ", "/Library/", "Applications/", "defaults write"):
        assert macos_only not in guide, \
            f"agent-setup.md has a macOS-only instruction: {macos_only!r}"


def test_agent_setup_relative_links_resolve():
    """Every relative markdown link in the guide points at a real file/dir."""
    guide = AGENT_SETUP.read_text()
    targets = re.findall(r"\]\(([^)]+)\)", guide)
    broken = []
    for target in targets:
        if target.startswith(("http://", "https://", "#")):
            continue
        path = (AGENT_SETUP.parent / target.split("#", 1)[0]).resolve()
        if not path.exists():
            broken.append(target)
    assert not broken, f"agent-setup.md has broken relative links: {broken}"


def test_mcp_json_snippet_parses():
    """Every fenced JSON snippet in the README and the setup guide is valid,
    and the guide carries the mcpServers block agents copy."""
    for doc in (README, AGENT_SETUP):
        for block in code_blocks(doc.read_text(), "json"):
            json.loads(block)  # raises if the snippet is not valid JSON
    guide_blocks = code_blocks(AGENT_SETUP.read_text(), "json")
    assert any("pet-tools-mcp" in b for b in guide_blocks), \
        "agent-setup.md needs a fenced json mcpServers snippet using pet-tools-mcp"


def test_readme_pet_commands_exist():
    valid = valid_mention_paths()  # leaf commands plus bare group names
    for doc in (README, AGENT_SETUP):
        unknown = {c for c in mentioned_commands(doc.read_text()) if c not in valid}
        assert not unknown, f"{doc} mentions nonexistent commands: {sorted(unknown)}"


def test_supported_machines_table_matches_profiles():
    """Every fact in the README model table is enforced against machines.py
    and the captured boot banners — the table cannot drift."""
    from petlib.machines import PROFILES
    text = README.read_text()
    idx = text.index("## Supported machines")
    end = text.index("\n## ", idx + 1)
    section = text[idx:end]
    rows = {}
    for line in section.splitlines():
        if line.startswith("| `pet"):
            cells = [c.strip() for c in line.strip("|").split("|")]
            rows[cells[0].strip("`")] = cells
    assert set(rows) == set(PROFILES), \
        f"table models {sorted(rows)} != profiles {sorted(PROFILES)}"
    for name, p in PROFILES.items():
        cells = rows[name]   # 0=model 1=ram 2=free 3=basic 4=screen 5=notes
        assert f"{p.ram_kb} KB" in cells[1], f"{name}: RAM cell {cells[1]!r}"
        assert BOOT_FREE[name] in cells[2], f"{name}: free cell {cells[2]!r}"
        assert p.basic_version in cells[3], f"{name}: BASIC cell {cells[3]!r}"
        assert f"{p.screen_cols}×{p.screen_rows}" in cells[4], \
            f"{name}: screen cell {cells[4]!r}"
