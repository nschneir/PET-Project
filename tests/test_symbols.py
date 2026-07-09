from petlib.symbols import load_labels, save_labels


def test_load_ld65_and_vice_forms(tmp_path):
    f = tmp_path / "prog.lbl"
    f.write_text(
        "al 00040D .start\n"
        "al C:0420 .loop\n"
        "al C:FFD2 .CHROUT\n"
        "; a comment line to ignore\n"
        "\n"
    )
    labels = load_labels(f)
    assert labels == {"start": 0x040D, "loop": 0x0420, "CHROUT": 0xFFD2}


def test_save_and_reload_roundtrip(tmp_path):
    f = tmp_path / "out.lbl"
    save_labels(f, {"main": 0x040D, "msg": 0x0430})
    text = f.read_text()
    assert "al C:040d .main" in text
    assert load_labels(f) == {"main": 0x040D, "msg": 0x0430}
