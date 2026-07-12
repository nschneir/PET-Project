import pytest

import petlib
from petlib.packaging import PackageError, package_program


def test_version():
    assert petlib.__version__ == "1.1.0"


def test_package_prg_copies_source(tmp_path):
    src = tmp_path / "game.prg"
    src.write_bytes(b"\x01\x04\x00\x00")
    package_program(src, out=str(tmp_path / "copy.prg"))
    assert (tmp_path / "copy.prg").read_bytes() == src.read_bytes()


def test_package_unknown_extension(tmp_path):
    with pytest.raises(PackageError, match="cannot package"):
        package_program(tmp_path / "x.txt")
