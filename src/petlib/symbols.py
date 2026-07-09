"""VICE label ("moncommands") files: `al C:080d .name` lines.

ld65 -Ln emits the same format without the C: memspace prefix; we accept both.
"""

from __future__ import annotations

import re
from pathlib import Path

_LABEL_RE = re.compile(r"^al\s+(?:C:)?([0-9A-Fa-f]+)\s+\.?(\S+)", re.IGNORECASE)


def load_labels(path: str | Path) -> dict[str, int]:
    labels: dict[str, int] = {}
    for line in Path(path).read_text().splitlines():
        m = _LABEL_RE.match(line.strip())
        if m:
            labels[m.group(2)] = int(m.group(1), 16)
    return labels


def save_labels(path: str | Path, labels: dict[str, int]) -> None:
    lines = [f"al C:{addr:04x} .{name}" for name, addr in sorted(labels.items(), key=lambda kv: kv[1])]
    Path(path).write_text("\n".join(lines) + "\n")
