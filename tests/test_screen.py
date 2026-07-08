from pathlib import Path
from unittest.mock import Mock

from PIL import Image

from petlib.machines import get_profile
from petlib.screen import read_screen_text, save_screenshot_png


def test_read_screen_text_uses_profile_geometry():
    profile = get_profile("pet4032")
    mon = Mock()
    screen = bytes([18, 5, 1, 4, 25, 46]) + bytes([32] * (1000 - 6))  # "READY."
    mon.memory_read.return_value = screen
    text = read_screen_text(mon, profile)
    mon.memory_read.assert_called_once_with(0x8000, 1000)
    assert text.splitlines()[0] == "READY."


def test_save_screenshot_png(tmp_path):
    mon = Mock()
    mon.display.return_value = (2, 2, bytes([0, 1, 1, 0]))
    mon.palette.return_value = [(0, 0, 0), (0, 255, 0)]
    out = tmp_path / "shot.png"
    w, h = save_screenshot_png(mon, out)
    assert (w, h) == (2, 2)
    img = Image.open(out).convert("RGB")
    assert img.size == (2, 2)
    assert img.getpixel((1, 0)) == (0, 255, 0)
    assert img.getpixel((0, 0)) == (0, 0, 0)
