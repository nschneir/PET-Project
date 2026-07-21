"""Helpers for docs-vs-reality tests."""

import re

import click

from petlib.cli import main


def _walk_tree() -> tuple[set[str], set[str]]:
    """(invocable command paths, group paths) from the real click tree."""
    commands: set[str] = set()
    groups: set[str] = set()

    def walk(cmd, prefix):
        if isinstance(cmd, click.Group):
            groups.add(prefix)
            if cmd.invoke_without_command:
                commands.add(prefix)
            for name, sub in cmd.commands.items():
                walk(sub, f"{prefix} {name}")
        else:
            commands.add(prefix)

    walk(main, "pet")
    return commands, groups


def all_command_paths() -> set[str]:
    return _walk_tree()[0]


def valid_mention_paths() -> set[str]:
    """Commands plus bare group names — both legitimate in prose."""
    commands, groups = _walk_tree()
    return commands | groups


def code_blocks(text: str, lang: str) -> list[str]:
    """Fenced ```lang code blocks; lang may be a regex alternation."""
    return re.findall(rf"```{lang}\n(.*?)```", text, re.S)


DOC_HEADING = re.compile(r"^### `(pet[^`]*)`(?: \(alias(?:es)?: (.+)\))?", re.M)


def documented_paths(doc_text: str) -> set[str]:
    """Heading paths, including aliases documented inline as
    '### `pet x remove` (alias: `pet x rm`)'."""
    out = set()
    for name, aliases in DOC_HEADING.findall(doc_text):
        out.add(name)
        if aliases:
            out.update(re.findall(r"`(pet[^`]*)`", aliases))
    return out


PET_MENTION = re.compile(r"`(pet(?: [a-z]+)+)\b")


def mentioned_commands(doc_text: str) -> set[str]:
    """`pet xyz ...` mentions in backticks, trimmed to known-prefix depth 3."""
    real = valid_mention_paths()
    out = set()
    for m in PET_MENTION.findall(doc_text):
        words = m.split()
        for depth in (3, 2, 1):
            cand = " ".join(words[:depth])
            if cand in real:
                out.add(cand)
                break
        else:
            out.add(m)  # unknown mention — will fail the subset check
    return out


# Boot-banner free bytes per model, captured from live xpet (plan Task 9).
# The README table and test_integration_vice both check against this.
BOOT_FREE = {
    "pet2001-4k": "3071",
    "pet2001": "7167",
    "pet3032": "31743",
    "pet4032": "31743",
    "pet8032": "31743",
    "pet8296": "31743",
}
