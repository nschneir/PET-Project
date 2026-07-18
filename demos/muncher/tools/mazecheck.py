#!/usr/bin/env python3
"""mazecheck.py — validate, pack, and emit Ms. Muncher maze maps.

Map vocabulary (28 cols x 25 rows):
  '#' wall   '.' dot   'O' energizer   ' ' open corridor (no dot)
  '=' ghost-house door (fixed cells 13/14 on row 10)
  'T' tunnel mouth (cols 0/27 on a declared tunnel row)

Packed form: 2 bits per cell, row-major, cell N in bits (2*(N%4)) of byte
N//4 — 175 bytes per maze. OPEN=0 DOT=1 ENERGIZER=2 WALL=3. The door and
tunnel mouths pack as OPEN: house geometry is identical in all four mazes
(spec §5), so the game hardcodes those coordinates.

Usage: mazecheck.py MAPS_DIR INC_DIR   -> validates every authored maze in
MAZES and writes INC_DIR/mapdata.inc (ca65 syntax) with packed maps and
per-maze scaled constants.
"""
import sys
from dataclasses import dataclass, field
from pathlib import Path

W, H = 28, 25
OPEN, DOT, ENERGIZER, WALL = 0, 1, 2, 3
CH = {"#": WALL, ".": DOT, "O": ENERGIZER, " ": OPEN, "=": OPEN, "T": OPEN}

# Fixed geometry (spec §5) — identical in all four mazes.
HOUSE_X0, HOUSE_X1 = 11, 16          # outer wall columns
HOUSE_TOP, HOUSE_BOT = 10, 12        # wall rows; row 11 = interior
DOOR = ((13, 10), (14, 10))
INTERIOR = tuple((x, 11) for x in range(12, 16))
START = ((13, 19), (14, 19))         # Ms. Muncher start cells (open, dotless)

# Per-maze authoring contract: tunnels + arcade dot data (spec §5 table).
MAZES = {
    1: dict(file="maze1.txt", tunnels=[6, 14], arcade_dots=220, target=172),
    2: dict(file="maze2.txt", tunnels=[1, 19], arcade_dots=240, target=188),
    3: dict(file="maze3.txt", tunnels=[7], arcade_dots=238, target=186),
    4: dict(file="maze4.txt", tunnels=[10, 13], arcade_dots=234, target=182),
}

# Arcade-measured Elroy stage-1 thresholds by board (spec §7); stage 2 = half.
ELROY1_BY_BOARD = {1: 0, 2: 7, 3: 7, 4: 7, 5: 7, 6: 39, 7: 39, 8: 39,
                   9: 49, 10: 49, 11: 49, 12: 59, 13: 59, 14: 59, 15: 79,
                   16: 79, 17: 79, 18: 89, 19: 89, 20: 89, 21: 89}
BOARD_MAZE = {1: 1, 2: 1, 3: 2, 4: 2, 5: 2, 6: 3, 7: 3, 8: 3, 9: 3,
              10: 4, 11: 4, 12: 4, 13: 4, 14: 3, 15: 3, 16: 3, 17: 3,
              18: 4, 19: 4, 20: 4, 21: 4}


class MazeError(ValueError):
    pass


@dataclass
class Maze:
    cells: list                       # 25 rows x 28 ints
    dots: int = 0
    energizers: list = field(default_factory=list)
    tunnel_rows: list = field(default_factory=list)


def parse(text):
    rows = [r for r in text.splitlines() if r != ""]
    if len(rows) != H or any(len(r) != W for r in rows):
        raise MazeError(f"map must be exactly {W}x{H} "
                        f"(got {len(rows)} rows, widths {sorted({len(r) for r in rows})})")
    bad = sorted({c for r in rows for c in r} - set(CH))
    if bad:
        raise MazeError(f"unknown map characters: {bad}")
    return rows


def validate(text, tunnel_rows, dot_target, tol=8):
    rows = parse(text)
    errs = []

    # mirror symmetry on the raw vocabulary (T<->T, =<->=, walls, dots)
    for y, r in enumerate(rows):
        if r != r[::-1]:
            errs.append(f"row {y} is not mirror-symmetric")

    # border closed except tunnel mouths
    for x in range(W):
        if rows[0][x] != "#" or rows[H - 1][x] != "#":
            errs.append(f"border open at top/bottom col {x}")
            break
    for y in range(1, H - 1):
        for x in (0, W - 1):
            want_mouth = y in tunnel_rows
            if want_mouth and rows[y][x] != "T":
                errs.append(f"tunnel row {y} lacks mouth at col {x}")
            if not want_mouth and rows[y][x] != "#":
                errs.append(f"border open at row {y} col {x} (not a tunnel row)")
    for y in tunnel_rows:
        for x in (1, W - 2):
            if rows[y][x] == "#":
                errs.append(f"tunnel row {y} blocked just inside the mouth")

    # ghost house geometry
    for x in range(HOUSE_X0, HOUSE_X1 + 1):
        exp_top = "=" if (x, HOUSE_TOP) in DOOR else "#"
        if rows[HOUSE_TOP][x] != exp_top:
            errs.append(f"house top row {HOUSE_TOP} col {x}: "
                        f"expected {exp_top!r}, got {rows[HOUSE_TOP][x]!r} (door/house)")
        if rows[HOUSE_BOT][x] != "#":
            errs.append(f"house bottom wall broken at col {x}")
    for x, y in INTERIOR:
        if rows[y][x] != " ":
            errs.append(f"house interior ({x},{y}) must be open ' '")
    if rows[11][HOUSE_X0] != "#" or rows[11][HOUSE_X1] != "#":
        errs.append("house side walls broken")
    for x, y in DOOR:
        if rows[y - 1][x] == "#":
            errs.append(f"cell above the door ({x},{y-1}) must be open")
    for x, y in START:
        if rows[y][x] != " ":
            errs.append(f"start cell ({x},{y}) must be open ' '")

    grid = [[CH[c] for c in r] for r in rows]
    ghost_only = set(DOOR) | set(INTERIOR)

    def open_neighbours(x, y):
        out = []
        for dx, dy in ((0, -1), (-1, 0), (0, 1), (1, 0)):
            nx, ny = x + dx, y + dy
            if nx < 0 or nx >= W:
                if y in tunnel_rows and ny == y:
                    out.append(((nx + W) % W, y))  # wrap through the tunnel
                continue
            if 0 <= ny < H and grid[ny][nx] != WALL and (nx, ny) not in ghost_only:
                out.append((nx, ny))
        return out

    # dead ends (corridor cells need >= 2 exits; house cells exempt)
    for y in range(H):
        for x in range(W):
            if grid[y][x] == WALL or (x, y) in ghost_only:
                continue
            if len(open_neighbours(x, y)) < 2:
                errs.append(f"dead end at ({x},{y})")

    # reachability of every dot/energizer from the start (door is ghost-only)
    seen = set()
    frontier = [START[0]]
    while frontier:
        cx, cy = frontier.pop()
        if (cx, cy) in seen:
            continue
        seen.add((cx, cy))
        frontier.extend(n for n in open_neighbours(cx, cy) if n not in seen)
    unreachable = [(x, y) for y in range(H) for x in range(W)
                   if grid[y][x] in (DOT, ENERGIZER) and (x, y) not in seen]
    if unreachable:
        errs.append(f"unreachable dots at {unreachable[:6]}"
                    + ("..." if len(unreachable) > 6 else ""))

    energizers = [(x, y) for y in range(H) for x in range(W)
                  if grid[y][x] == ENERGIZER]
    if len(energizers) != 4:
        errs.append(f"expected 4 energizers, found {len(energizers)}")
    if any(x not in (1, W - 2) for x, y in energizers):
        errs.append("energizers must sit in the corner columns 1/26")

    dots = sum(r.count(DOT) for r in grid)
    if abs(dots - dot_target) > tol:
        errs.append(f"dot count {dots} outside target {dot_target}±{tol}")

    if errs:
        raise MazeError("; ".join(errs))
    return Maze(cells=grid, dots=dots, energizers=energizers,
                tunnel_rows=list(tunnel_rows))


def pack(maze):
    flat = [c for row in maze.cells for c in row]
    out = bytearray()
    for i in range(0, len(flat), 4):
        b = 0
        for j, c in enumerate(flat[i:i + 4]):
            b |= c << (2 * j)
        out.append(b)
    return bytes(out)


def unpack(packed):
    flat = []
    for b in packed:
        for j in range(4):
            flat.append((b >> (2 * j)) & 3)
    return [flat[y * W:(y + 1) * W] for y in range(H)]


def scale(value, dots, arcade_dots):
    """Scale an arcade dot-count threshold to an adapted maze (spec §5)."""
    return round(value * dots / arcade_dots)


def emit(mazes, inc_path):
    lines = ["; mapdata.inc — GENERATED by tools/mazecheck.py; do not edit.", ""]
    for n, maze in sorted(mazes.items()):
        spec = MAZES[n]
        lines += [
            f"MAZE{n}_DOTS = {maze.dots}",
            f"MAZE{n}_FRUIT1_EATEN = {scale(64, maze.dots, spec['arcade_dots'])}",
            f"MAZE{n}_FRUIT2_LEFT = {scale(66, maze.dots, spec['arcade_dots'])}",
        ]
    if set(mazes) == set(MAZES):  # Elroy tables need every maze's dot ratio
        e1 = [scale(ELROY1_BY_BOARD[b], mazes[BOARD_MAZE[b]].dots,
                    MAZES[BOARD_MAZE[b]]["arcade_dots"]) for b in range(1, 22)]
        lines.append("elroy1_tbl: .byte " + ", ".join(map(str, e1))
                     + " ; boards 1-21, dots-left stage 1")
        lines.append("elroy2_tbl: .byte " + ", ".join(str(v // 2) for v in e1)
                     + " ; stage 2 = half")
    for n, maze in sorted(mazes.items()):
        packed = pack(maze)
        lines.append(f"maze{n}_map:")
        for i in range(0, len(packed), 16):
            chunk = ", ".join(f"${b:02X}" for b in packed[i:i + 16])
            lines.append(f"        .byte {chunk}")
    Path(inc_path).write_text("\n".join(lines) + "\n")


def main(maps_dir, inc_dir):
    mazes = {}
    for n, spec in MAZES.items():
        p = Path(maps_dir) / spec["file"]
        if not p.exists():
            print(f"maze {n}: {spec['file']} not authored yet — skipped")
            continue
        maze = validate(p.read_text(), tunnel_rows=spec["tunnels"],
                        dot_target=spec["target"])
        mazes[n] = maze
        print(f"maze {n}: OK — {maze.dots} dots "
              f"(target {spec['target']}±8), tunnels {spec['tunnels']}")
    if not mazes:
        sys.exit("no mazes authored")
    out = Path(inc_dir) / "mapdata.inc"
    emit(mazes, out)
    print(f"wrote {out}")


if __name__ == "__main__":
    if len(sys.argv) != 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2])
