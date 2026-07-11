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
    ram_kb: int                 # total RAM (pet8296: banked; BASIC sees 32K)


def _pet(name: str, model: str, basic: str, cols: int, ram_kb: int,
         extra_args: tuple[str, ...] = ()) -> MachineProfile:
    return MachineProfile(
        name=name,
        vice_emulator="xpet",
        vice_args=("-model", model, *extra_args),
        basic_version=basic,
        basic_start=0x0401,
        screen_addr=0x8000,
        screen_cols=cols,
        screen_rows=25,
        ram_kb=ram_kb,
    )


PROFILES: dict[str, MachineProfile] = {
    p.name: p
    for p in (
        # The PET 2001 shipped in 4K and 8K configurations (2001-4 / 2001-8).
        _pet("pet2001-4k", "2001", "1.0", 40, 4, extra_args=("-ramsize", "4")),
        _pet("pet2001", "2001", "1.0", 40, 8),
        _pet("pet3032", "3032", "2.0", 40, 32),
        _pet("pet4032", "4032", "4.0", 40, 32),
        _pet("pet8032", "8032", "4.0", 80, 32),
        _pet("pet8296", "8296", "4.0", 80, 128),
    )
}


def get_profile(name: str) -> MachineProfile:
    try:
        return PROFILES[name]
    except KeyError:
        raise KeyError(
            f"unknown machine profile {name!r}; available: {', '.join(sorted(PROFILES))}"
        ) from None
