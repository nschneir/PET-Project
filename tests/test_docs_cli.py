from pathlib import Path

from tests.doc_helpers import all_command_paths, documented_paths

DOC = Path("docs/cli.md")


def test_every_command_documented_and_vice_versa():
    documented = documented_paths(DOC.read_text())
    actual = all_command_paths()
    missing = actual - documented
    stale = documented - actual
    assert not missing, f"commands lacking a '### `pet ...`' entry: {sorted(missing)}"
    assert not stale, f"documented commands that do not exist: {sorted(stale)}"


def test_inventory_size_sanity():
    assert len(all_command_paths()) >= 35
