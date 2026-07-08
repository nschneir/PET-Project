"""PET character conversions.

Screen RAM holds *screen codes* (not PETSCII): 0='@', 1-26='A'-'Z',
27-31='[' '\\' ']' up-arrow left-arrow, 32-63 match ASCII 0x20-0x3F,
64-127 are graphics glyphs, bit 7 = reverse video.
This is the uppercase/graphics character set; lowercase mode is out of
scope for v1 (tracked for the business-keyboard models).
"""

from __future__ import annotations

_LOW = "@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\\]^_"          # codes 0-31 (^ = up arrow, _ = left arrow)
_MID = ' !"#$%&\'()*+,-./0123456789:;<=>?'          # codes 32-63
GRAPHICS_PLACEHOLDER = "·"

# graphics codes with a reasonable ASCII-art equivalent
_GRAPHICS = {64: "-", 66: "|", 91: "+", 96: " "}     # horiz bar, vert bar, cross, shifted space


def screen_code_to_char(code: int) -> str:
    code &= 0x7F  # strip reverse-video bit
    if code < 32:
        return _LOW[code]
    if code < 64:
        return _MID[code - 32]
    return _GRAPHICS.get(code, GRAPHICS_PLACEHOLDER)


def screen_to_text(data: bytes, cols: int) -> str:
    rows = []
    for i in range(0, len(data), cols):
        row = "".join(screen_code_to_char(c) for c in data[i : i + cols])
        rows.append(row.rstrip())
    return "\n".join(rows).rstrip("\n")


def ascii_to_petscii(s: str) -> bytes:
    out = bytearray()
    for ch in s:
        if ch in ("\n", "\r"):
            out.append(0x0D)
            continue
        ch = ch.upper()
        code = ord(ch)
        if 0x20 <= code <= 0x5D:  # space..'?', '@', 'A'-'Z', '[' '\\' ']'
            out.append(code)
        else:
            raise ValueError(f"cannot map {ch!r} to PETSCII for keyboard input")
    return bytes(out)
