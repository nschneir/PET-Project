"""Machine profiles: everything model-specific is data here, not code elsewhere.

Adding a machine (e.g. VIC-20 later) means adding a profile, not new code paths.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class MachineProfile:
    name: str
    vice_emulator: str          # VICE binary, e.g. "xpet"
    vice_args: tuple[str, ...]  # model selection args
    basic_version: str          # "1.0" | "2.0" | "4.0"
    basic_start: int            # BASIC program load address
    screen_addr: int            # screen RAM base
    screen_cols: int
    screen_rows: int


def _pet(name: str, model: str, basic: str, cols: int) -> MachineProfile:
    return MachineProfile(
        name=name,
        vice_emulator="xpet",
        vice_args=("-model", model),
        basic_version=basic,
        basic_start=0x0401,
        screen_addr=0x8000,
        screen_cols=cols,
        screen_rows=25,
    )


PROFILES: dict[str, MachineProfile] = {
    p.name: p
    for p in (
        _pet("pet2001", "2001", "1.0", 40),
        _pet("pet3032", "3032", "2.0", 40),
        _pet("pet4032", "4032", "4.0", 40),
        _pet("pet8032", "8032", "4.0", 80),
        _pet("pet8296", "8296", "4.0", 80),
    )
}


def get_profile(name: str) -> MachineProfile:
    try:
        return PROFILES[name]
    except KeyError:
        raise KeyError(
            f"unknown machine profile {name!r}; available: {', '.join(sorted(PROFILES))}"
        ) from None
