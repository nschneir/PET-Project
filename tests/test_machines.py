import pytest

from petlib.machines import PROFILES, get_profile


def test_all_v1_models_present():
    assert set(PROFILES) == {"pet2001", "pet3032", "pet4032", "pet8032", "pet8296"}


def test_pet4032_profile():
    p = get_profile("pet4032")
    assert p.vice_emulator == "xpet"
    assert p.vice_args == ("-model", "4032")
    assert p.basic_version == "4.0"
    assert p.basic_start == 0x0401
    assert p.screen_addr == 0x8000
    assert (p.screen_cols, p.screen_rows) == (40, 25)


def test_80_column_models():
    assert get_profile("pet8032").screen_cols == 80
    assert get_profile("pet8296").screen_cols == 80


def test_unknown_profile_lists_available():
    with pytest.raises(KeyError, match="pet4032"):
        get_profile("c64")
