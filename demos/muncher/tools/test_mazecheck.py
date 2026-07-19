"""Unit tests for mazecheck.py — the Ms. Muncher maze validator/packer.

The synthetic fixture is a maximally-dotted grid maze: every interior cell
is a dot except the ghost house block and the player start cells. It is
symmetric, dead-end free (grid interior), and fully reachable, so each test
can break exactly one property.
"""
import pytest

import mazecheck as mc

TUNNELS = [6]


def synthetic(tunnels=TUNNELS):
    rows = []
    for y in range(25):
        if y == 0 or y == 24:
            rows.append("#" * 28)
            continue
        edge = "T" if y in tunnels else "#"
        rows.append(edge + "." * 26 + edge)
    g = [list(r) for r in rows]
    # ghost house (spec §5): walls cols 11-16 rows 10-12, door at (13,10),(14,10)
    for x in range(11, 17):
        g[10][x] = "#"
        g[12][x] = "#"
    g[10][13] = g[10][14] = "="
    g[11][11] = g[11][16] = "#"
    for x in range(12, 16):
        g[11][x] = " "
    # energizers in the four corner regions, cols 1/26
    for y, x in ((2, 1), (2, 26), (21, 1), (21, 26)):
        g[y][x] = "O"
    # player start cells: open, dotless
    g[19][13] = g[19][14] = " "
    return "\n".join("".join(r) for r in g)


def target_of(text):
    return sum(row.count(".") for row in text.splitlines())


def check(text, tunnels=TUNNELS, target=None):
    return mc.validate(text, tunnel_rows=tunnels,
                       dot_target=target_of(text) if target is None else target)


def test_valid_synthetic_passes():
    maze = check(synthetic())
    assert maze.dots == target_of(synthetic())
    assert len(maze.energizers) == 4


def test_shape_enforced():
    bad = "\n".join(r[:-1] for r in synthetic().splitlines())  # 27 cols
    with pytest.raises(mc.MazeError, match="28"):
        check(bad)


def test_symmetry_enforced():
    g = [list(r) for r in synthetic().splitlines()]
    g[3][1] = "#"  # break mirror without touching border
    with pytest.raises(mc.MazeError, match="[Ss]ymmet"):
        check("\n".join("".join(r) for r in g))


def test_border_hole_rejected():
    g = [list(r) for r in synthetic().splitlines()]
    g[8][0] = "."  # hole in the left border on a non-tunnel row (both sides,
    g[8][27] = "."  # to keep symmetry: must still be rejected)
    with pytest.raises(mc.MazeError, match="[Bb]order"):
        check("\n".join("".join(r) for r in g))


def test_tunnel_mouths_required():
    with pytest.raises(mc.MazeError, match="[Tt]unnel"):
        check(synthetic(tunnels=[6]), tunnels=[6, 14])  # row 14 lacks mouths


def test_house_geometry_enforced():
    g = [list(r) for r in synthetic().splitlines()]
    g[10][13] = g[10][14] = "#"  # brick up the door
    with pytest.raises(mc.MazeError, match="[Dd]oor|[Hh]ouse"):
        check("\n".join("".join(r) for r in g))


def test_dead_end_rejected():
    g = [list(r) for r in synthetic().splitlines()]
    # carve a one-cell pocket: open cell surrounded by three walls
    for x in range(2, 26):
        g[2][x] = "#" if g[2][x] == "." else g[2][x]
        g[3][x] = "#" if g[3][x] == "." else g[3][x]
    g[2][4] = "."   # pocket cell, reachable only from below... make it sealed
    g[2][23] = "."  # mirror partner
    g[3][4] = "."
    g[3][23] = "."
    g[4][4] = "."
    g[4][23] = "."
    # (2,4) has neighbours (1,4)='.' above? row1 is all dots — so instead seal it:
    g[1][4] = "#"
    g[1][23] = "#"
    # now (2,4)-(3,4)-(4,4) is a corridor whose top cell has 1 open neighbour
    with pytest.raises(mc.MazeError, match="[Dd]ead"):
        check("\n".join("".join(r) for r in g))


def test_unreachable_dot_rejected():
    g = [list(r) for r in synthetic().splitlines()]
    # wall off the bottom-left corner cell, leaving a dot inside
    g[22][2] = "#"
    g[23][3] = "#"
    g[22][25] = "#"
    g[23][24] = "#"
    # (23,1)/(23,2)... construct: cell (23,1) dot enclosed by border+walls
    g[22][1] = "#"
    g[22][26] = "#"
    with pytest.raises(mc.MazeError, match="[Rr]each|[Dd]ead"):
        check("\n".join("".join(r) for r in g))


def test_dot_count_tolerance():
    with pytest.raises(mc.MazeError, match="[Dd]ot count"):
        check(synthetic(), target=target_of(synthetic()) - 9)  # beyond ±8


def test_pack_roundtrip():
    maze = check(synthetic())
    packed = mc.pack(maze)
    assert len(packed) == 175
    assert mc.unpack(packed) == maze.cells


def test_scaling():
    assert mc.scale(64, 172, 220) == 50   # round(64*172/220) = 50.03 -> 50
    assert mc.scale(66, 172, 220) == 52   # 51.6 -> 52
    assert mc.scale(89, 186, 238) == 70   # elroy-style value


def test_real_maze1_if_present():
    import pathlib
    p = pathlib.Path(__file__).resolve().parent.parent / "maps" / "maze1.txt"
    if not p.exists():
        pytest.skip("maze1.txt not authored yet")
    spec = mc.MAZES[1]
    maze = mc.validate(p.read_text(), tunnel_rows=spec["tunnels"],
                       dot_target=spec["target"])
    assert abs(maze.dots - spec["target"]) <= 8


def test_fruit_paths_validate_on_real_maze1():
    import pathlib
    p = pathlib.Path(__file__).resolve().parent.parent / "maps" / "maze1.txt"
    if not p.exists():
        pytest.skip("maze1.txt not authored yet")
    spec = mc.MAZES[1]
    maze = mc.validate(p.read_text(), tunnel_rows=spec["tunnels"],
                       dot_target=spec["target"])
    mc.validate_fruit_paths(1, maze)  # raises on any off-corridor step


def test_fruit_path_walk_rejects_walls():
    maze = check(synthetic())
    with pytest.raises(mc.MazeError, match="corridor"):
        mc.walk((1, 1), [("U", 1)], maze.cells)  # into the border
