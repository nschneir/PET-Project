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


DOC_HEADING = re.compile(r"^### `(pet[^`]*)`", re.M)


def documented_paths(doc_text: str) -> set[str]:
    return set(DOC_HEADING.findall(doc_text))


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
