"""Read the PET screen as text (via screen RAM) or as a PNG (via display get)."""

from __future__ import annotations

from pathlib import Path

from PIL import Image

from .machines import MachineProfile
from .monitor import MonitorClient
from .text import screen_to_text


def read_screen_text(mon: MonitorClient, profile: MachineProfile) -> str:
    size = profile.screen_cols * profile.screen_rows
    data = mon.memory_read(profile.screen_addr, size)
    return screen_to_text(data, profile.screen_cols)


def save_screenshot_png(mon: MonitorClient, path: str | Path) -> tuple[int, int]:
    width, height, pixels = mon.display()
    palette = mon.palette()
    img = Image.new("P", (width, height))
    flat = []
    for r, g, b in palette:
        flat += [r, g, b]
    img.putpalette(flat)
    img.putdata(list(pixels))
    img.save(Path(path), format="PNG")
    return width, height
