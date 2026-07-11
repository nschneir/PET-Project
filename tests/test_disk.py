import shutil

import pytest

from petlib.disk import (
    DiskError,
    create_image,
    drive_type_for,
    get_file,
    list_files,
    put_file,
)


def test_drive_type_for():
    assert drive_type_for("a.d64") == 2031
    assert drive_type_for("b.D80") == 8050
    assert drive_type_for("c.d82") == 8250
    with pytest.raises(DiskError, match="d71"):
        drive_type_for("x.d71")


def test_missing_c1541_message(monkeypatch, tmp_path):
    monkeypatch.delenv("PET_TOOLS_C1541", raising=False)
    monkeypatch.setattr("petlib.disk.shutil.which", lambda n: None)
    with pytest.raises(DiskError, match="[Ii]nstall"):
        create_image(tmp_path / "x.d64")


needs_c1541 = pytest.mark.skipif(
    shutil.which("c1541") is None, reason="c1541 not installed"
)


@needs_c1541
def test_real_c1541_roundtrip(tmp_path):
    img = create_image(tmp_path / "t.d64", label="testdisk", disk_id="01")
    assert img.exists() and img.stat().st_size > 0

    src = tmp_path / "prog.prg"
    src.write_bytes(b"\x01\x04hello")
    name = put_file(img, src, "demo")
    assert name == "demo"

    d = list_files(img)
    assert d["label"].strip() == "testdisk"
    assert d["files"][0]["name"] == "demo" and d["files"][0]["type"] == "prg"
    assert d["blocks_free"] > 0

    out = get_file(img, "demo", tmp_path / "out.prg")
    assert out.read_bytes() == src.read_bytes()


@needs_c1541
def test_real_c1541_d80(tmp_path):
    img = create_image(tmp_path / "t.d80")
    assert img.stat().st_size > 500_000  # 77-track image is big


def test_c1541_failure_raises_disk_error(tmp_path, monkeypatch):
    import subprocess

    from petlib import disk

    def fail(cmd, capture_output, text):
        return subprocess.CompletedProcess(cmd, 1, stdout="", stderr="bad image")
    monkeypatch.setattr(disk.subprocess, "run", fail)
    with pytest.raises(disk.DiskError, match="bad image"):
        disk.list_files(tmp_path / "x.d64")


def test_get_file_missing_output_raises(tmp_path, monkeypatch):
    import subprocess

    from petlib import disk

    def ok_but_writes_nothing(cmd, capture_output, text):
        return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")
    monkeypatch.setattr(disk.subprocess, "run", ok_but_writes_nothing)
    with pytest.raises(disk.DiskError, match="was not written"):
        disk.get_file(tmp_path / "x.d64", "game", tmp_path / "out.prg")
