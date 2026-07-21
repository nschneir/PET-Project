# `pet` CLI reference

A complete reference for the `pet` command line — everything the toolset can
do without the MCP server. For MCP-native clients the `pet-tools-mcp` server
exposes the same operations; see the README.

## Conventions

- **Sessions.** Most commands act on a running emulator session. Sessions are
  tracked in a registry under `~/.pet-tools/sessions/` (override the base with
  `$PET_TOOLS_HOME`). A command with no `--session` targets the single running
  session; if several are running you must name one.
- **Global options** (before the subcommand):
  - `--json` — emit machine-readable JSON on stdout instead of human text.
    This is the intended interface for AI agents. Every command supports it.
  - `--session, -s NAME` — target a specific session by name.
  - `--version` — print `pet <version>` and exit.
  - `--help` — print usage and exit. Works on every command and group
    (e.g. `pet session start --help`).
- **Numbers.** Address and value arguments accept `$hex` (e.g. `$8000`),
  `0xhex`, or decimal. Where a label file is registered on the session (via
  `pet build`/`pet run` of assembly, or `pet load --symbols`), a **symbol
  name** is accepted anywhere an address is. Addresses additionally accept
  an **offset** (`alienX+49`, `tick-1`, `dots+$52`, `$8000+40`) and a
  **screen cell** `@row,col`
  (e.g. `@23,18`), resolved against the session model's real screen base
  and width — 40 vs 80 columns handled for you.
- **Exit codes.** `0` on success; `1` on error, on a `pet wait` timeout, or on
  a failing `pet test`.
- **Machine state.** Every session runs a monitor daemon that owns the one
  VICE connection, so the machine's run/stop state persists across `pet`
  commands. **`pet step`**, **`pet finish`**, **`pet until`**, and
  **`pet wait --break`** (on a checkpoint hit) halt the machine, and it
  STAYS halted — across as many commands as you like — until
  `pet continue`, an explicitly-resuming command (`pet run`, `pet load`,
  `pet disk boot`, `pet session reset`), or a new halt. Inspection commands
  (`screen`, `mem`, `reg`, ...) never disturb the state.

---

## Help and version

### `pet help`

Print help for `pet` or one of its commands, then exit. Equivalent to the
`--help` option, but as a subcommand.

- `COMMAND...` (optional) — a command path to describe; with no argument,
  prints the top-level help.

Examples: `pet help`, `pet help session`, `pet help session start`. No
session required.

---

## Sessions

### `pet session start`

Boot a fresh emulated PET.

- `--model MODEL` (default `pet4032`) — one of `pet2001-4k`, `pet2001`,
  `pet3032`, `pet4032`, `pet8032`, `pet8296` (see the README's Supported
  machines table).
- `-s, --name NAME` — session name (defaults to the model name).
- `--headless` — suppress the VICE window (video/audio dummied).
- `--warp` — run at maximum speed (recommended for automation).
- `--disk PATH` — attach a `.d64`/`.d80`/`.d82` image to drive 8 at boot.

Human: `started pet4032 session 'pet4032' (pid 1234, monitor port 6510)`.
JSON: `{"name", "model", "pid", "port"}`. Machine left running.

Starting a session also starts its monitor daemon — the process that owns
the VICE monitor connection and holds run/stop state between commands.
Daemon output goes to `<sessions-dir>/<name>.daemon.log`; a crashed daemon
is respawned automatically by the next command (repeated crashes error out
and ask for a session restart). `PET_TOOLS_NO_DAEMON=1` disables it.

### `pet session list`

List running sessions (dead ones are pruned).
JSON: `{"sessions": [{"name", "model", "pid", "port"}, ...]}`.

### `pet session stop`

Stop a session and remove its registry record.

- `NAME` (optional) — the session to stop; defaults to the current one.
- `-s, --name NAME` — the same, as an option (the spelling every command
  understands). Giving both forms with different names is an error.

JSON: `{"stopped": NAME}`.

### `pet session reset`

Reset the running machine; leaves it running.

- `--hard` — power-cycle instead of a soft reset.

JSON: `{"reset": NAME, "hard": bool}`.

### `pet status`

    pet status

Show the current session (name, model, pid, port) and whether the machine
is **running** or **stopped** right now. The state comes from the session
daemon's own tracking — no emulator traffic, so it never disturbs the
machine. Without a daemon it reports `unknown` (a direct monitor
connection stops the CPU, making the question unanswerable). `pet reg`
also includes `"state"` in its JSON output.

---

## Screen

### `pet screen`

Show the emulated screen. With no option, prints the screen decoded to text —
the preferred way to observe program output. With `--png` it writes an image;
with `--codes` it prints the raw screen-code matrix.

- `--png PATH` — save a PNG screenshot instead of printing text.
- `--scale N` — integer nearest-neighbour upscale for `--png` (default 1;
  PET screens read better at 2–3×).
- `--codes` — print the 25×40 matrix of raw screen codes (decimal). With
  `--json`, nested arrays under `"codes"`. Use this to assert exact glyph
  identity.
- `--style unicode|ascii` — text decoding style (default `unicode`).
  Unicode maps graphics to real box/block/shape glyphs (`╭─╮ ● ▌ █ …`);
  `ascii` is the legacy conservative mapping (graphics → `·` except
  `- | +`).
- `--ansi-reverse` — wrap reverse-video cells with no Unicode complement
  in terminal inverse-video escapes.

JSON (text): `{"text", "rows": [...]}`. JSON (`--png`): `{"png", "width",
"height"}`. JSON (`--codes`): `{"codes": [[...], ...]}`. Machine state
preserved.

> **Migration note (v1.2):** the default decoding changed from the
> conservative ASCII mapping to Unicode. `pet wait --text` and YAML
> `wait: {text: ...}` match against the decoded text, so patterns that
> relied on graphics decoding to `·` (or reverse-space decoding to blank)
> must be updated or run with `--style ascii`. Plain-text patterns
> (letters/digits/punctuation) are unaffected.

---

## Keyboard

### `pet key type`

Type text into the running PET's keyboard buffer (`\n` = RETURN). Use it to
answer `INPUT` prompts or drive menus; for typing in whole programs prefer
`pet basic type`. Buffered keys never touch the live key-down state at `$97`
— to steer a game that reads held keys, use `pet key hold`.

- `TEXT` — the keystrokes (letters are case-folded to the PET's convention).

JSON: `{"typed_chars"}`. Machine state preserved.

### `pet key hold`

Hold KEY down for N game ticks by re-poking the key-down byte `$97` before
each one: write the key's PETSCII, run to the frame anchor, repeat. The
machine ends **stopped** at the anchor (resume with `pet continue`). BASIC 4
models only — `$97` holds a raw matrix index on BASIC 2 machines. For a
fully deterministic first frame, stop at the anchor first (`pet until REF`).

- `KEY` — one character, or `space`.
- `--at REF` (required) — the frame anchor: a label or address executed once
  per game tick (your main-loop label).
- `--frames N` (default `1`) — how many ticks to hold the key across.
- `--timeout SECS` (default `30`) — per-frame wait limit.

JSON: `{"registers", "pc_symbol", "stopped": true, "frames"}`. On a frame
timeout: exit 1, machine left running, checkpoint removed.

---

## Memory

### `pet mem read`

Read emulated memory and print a hex dump (16 bytes/line with an ASCII column).

- `ADDR` — start address (`$hex`/`0x`/decimal/symbol).
- `LENGTH` (default `256`) — number of bytes.
- `--decimal` — render decimal values instead of a hex dump.

JSON: `{"addr", "length", "hex", "bytes"}` (`hex` is the bytes hex-encoded;
`"bytes"` is always present as a decimal int array). Machine state
preserved.

### `pet mem get`

    pet mem get ADDR [LENGTH]

Print LENGTH (default 1) byte values at ADDR in decimal — bare,
space-separated, pipe-friendly (`[ $(pet mem get score) -gt 0 ]`). JSON:
`{"addr": N, "values": [ints]}`. ADDR is `$hex`/`0x`/decimal or a symbol
from the loaded label file. Does not disturb run/stop state. (MCP note:
there is deliberately no `pet_mem_get` tool — `pet_mem_read` already
returns a decimal `bytes` array.)

### `pet mem find`

    pet mem find VALUE... [--start ADDR] [--length N] [--limit M]

Search memory for a byte pattern and print every match address. VALUE is
one or more bytes (`$hex`/`0x`/decimal) forming the pattern. Defaults:
`--start $0000`, `--length $10000` (clamped to the 64 KB space),
`--limit 256`. JSON: `{"pattern", "start", "length", "matches", "count",
"truncated"}` — `truncated` is true when the limit clipped the list
(searching for `$00` legitimately matches thousands of addresses). Does
not disturb run/stop state.

### `pet mem write`

Write bytes to emulated memory.

- `ADDR` — start address (`$hex`/`0x`/decimal/symbol).
- `VALUES...` — one or more byte values (`$hex`/`0x`/decimal).

JSON: `{"addr", "written"}`. Machine state preserved.

---

## Registers

### `pet reg`

Show the CPU registers (this is a callable group — run it with no subcommand).
PC is annotated with the nearest symbol when a label file is loaded.

JSON: `{"registers": {"PC", "A", "X", "Y", "SP", "FL", ...}, "pc_symbol"}`.
Machine state preserved.

### `pet reg set`

Set a register.

- `NAME` — register name (e.g. `PC`, `A`, `X`, `Y`).
- `VALUE` — new value (`$hex`/`0x`/decimal).

JSON: `{"register", "value"}`. Machine state preserved.

---

## Breakpoints and watchpoints

Breakpoints and watchpoints are VICE checkpoints. Setting one leaves the
machine running; use `pet wait --break` to block until it fires. Checkpoints
survive a subsequent `pet load`/`pet run`, so set them before loading.

Checkpoints **persist across `pet run`/rebuilds by design** — reloading a
program does not remove them. Clear stale ones (`pet break clear`,
`pet watch clear`) or duplicates accumulate.

### `pet break add`

Set an execution breakpoint at an address or symbol.

- `REF` — address or symbol.
- `--condition EXPR` — a VICE condition, e.g. `'A != 0'`.
- `--temporary` — delete the breakpoint after it fires once.

JSON: `{"id", "address", "condition", "temporary"}`. Machine state preserved.

### `pet break list`

List all checkpoints with hit counts.
JSON: `{"breakpoints": [{"id", "address", "end", "op", "enabled", "hits",
"has_condition"}, ...]}`.

### `pet break remove`

- `CK_ID` — checkpoint id (integer). JSON: `{"removed": id}`.

### `pet break enable`

- `CK_ID` — checkpoint id. JSON: `{"enabled": id}`.

### `pet break disable`

- `CK_ID` — checkpoint id. JSON: `{"disabled": id}`.

### `pet break clear`

    pet break clear

Remove ALL breakpoints (exec checkpoints); watchpoints are kept. JSON:
`{"removed": [ids], "count": n}`.

### `pet watch add`

Set a watchpoint on a memory range (default: both load and store).

- `REF` — address or symbol.
- `--load` — break on reads.
- `--store` — break on writes.
- `--length N` (default `1`) — number of bytes to watch.

JSON: `{"id", "address", "length", "op"}`. Machine state preserved.

### `pet watch clear`

    pet watch clear

Remove ALL watchpoints (load/store checkpoints); breakpoints are kept.
JSON: `{"removed": [ids], "count": n}`.

---

## Execution control

### `pet step`

Execute N instructions; **the machine stays stopped** afterwards.

- `COUNT` (default `1`) — number of instructions.
- `--over` — step over `JSR` subroutines.

JSON: `{"registers", "pc_symbol", "stopped": true}`.

### `pet finish`

Run until the current subroutine returns; **stays stopped**.
JSON: `{"registers", "pc_symbol", "stopped": true}`.

### `pet continue`

Resume a stopped machine. JSON: `{"running": true}`.

### `pet until`

Run until `REF` (address or symbol) is executed; **stays stopped** there —
across subsequent commands — until you `pet continue`.

- `REF` — address or symbol.
- `--count N` (default `1`) — stop at the Nth arrival at REF. With REF set
  to the program's main-loop label this is deterministic **frame stepping**
  (see the cookbook's frame-stepping recipe). The count loop runs inside
  the session daemon, so large counts are fast (hundreds of frames per
  second of wall clock, not one per half-second).
- `--timeout SECS` (default `30`).

JSON: `{"registers", "pc_symbol", "stopped": true, "count"}`. Exit 1 on
timeout (the error reports how many arrivals were reached); after a timeout
the machine is left running and the checkpoint is removed.

On timeout `pet until` exits 1, **leaves the machine RUNNING**, and removes
the checkpoint it set (JSON: `"machine": "running"`,
`"checkpoint_removed": true`). Beware the branch-away deadlock: if the
program can stop visiting REF (death, menu, pause screen), `until REF` can
never fire — set a breakpoint at a code path that must still execute and use
`pet wait --break` instead.

---

## Waiting

### `pet wait`

Block until exactly one condition fires; reports which one. This is the primary
synchronization primitive for scripted use.

- `--text STR` — wait until STR appears on the screen.
- `--mem ADDR=VALUE` — wait until the byte at ADDR equals VALUE (e.g.
  `'$1000=42'`).
- `--break` — wait until a checkpoint fires; **leaves the machine stopped**.
- `--timeout SECS` (default `30`).

Exactly one of `--text`/`--mem`/`--break` is required. JSON on fire:
`{"fired": "text"|"mem", "elapsed"}` or `{"fired": "break", "checkpoint",
"pc", "pc_symbol", "elapsed"}`. Exit 1 on timeout (the error carries the last
screen for `--text`).

On timeout `pet wait` exits 1 and the machine is **left running**;
checkpoints you set remain set (JSON gains `"machine": "running"`).

---

## Building

### `pet build`

Assemble 6502 source (ca65 syntax) to a `.prg` plus a VICE label file.

- `SOURCE` — the `.s` file.
- `-o, --output PATH` — output `.prg` (defaults next to the source).
- `--model MODEL` (default `pet4032`) — selects the BASIC load address.

JSON: `{"prg", "labels"}`. No session required.

### `pet package`

Package a program into an artifact any VICE user can run — a bare `.prg`, or
a disk image with the program as its first (autostart) file. Pure file
operation; no session required.

- `SOURCE` — a `.s`, `.bas`, or `.prg` file (assembled/tokenized as needed).
- `-o, --output PATH` — the artifact; the extension picks the format:
  `.d64`/`.d80`/`.d82` build the `.prg` and write it to a fresh image
  (the `.prg` is kept beside it); `.prg` (or omitted) builds just the
  program file. Existing outputs are overwritten.
- `--title NAME` — the CBM file/disk name (uppercased, max 16 characters;
  defaults to the source stem).
- `--model MODEL` (default `pet4032`) — selects the BASIC load address and
  is pinned in the reported run command.

The recipient needs only stock VICE: `xpet -model 4032 game.d64` (or the
`.prg`) autostarts it, and from inside the emulator `LOAD"NAME",8` then
`RUN` works the traditional way. No ROMs or pet-tools ship in the artifact.
The `-model` flag matters: stock xpet boots its own default model, and ROM
behavior differs silently between BASIC generations (the `$97` key-down
byte holds PETSCII on BASIC 4 but a matrix index on BASIC 2 — a shipped
game's keyboard can go dead with an identical-looking screen).

JSON: `{"prg", "image", "title", "run"}` — `run` is the exact command to
hand to the recipient (model pinned); `image` is `null` for `.prg`-only
output.

---

## BASIC

### `pet basic tokenize`

Tokenize a BASIC source file to a `.prg` with `petcat`.

- `SOURCE` — the `.bas` file. **petcat convention: keywords and string text
  must be lowercase** (lowercase ASCII becomes unshifted PETSCII, which
  displays as uppercase on the PET).
- `-o, --output PATH` — output `.prg`.
- `--model MODEL` (default `pet4032`) — selects the BASIC dialect.

JSON: `{"prg"}`. No session required.

### `pet basic detokenize`

Print a `.prg` back as a BASIC listing.

- `PRG` — the tokenized program.
- `--model MODEL` (default `pet4032`).

JSON: `{"listing"}`. No session required.

### `pet basic type`

Type a BASIC program into the running PET through the keyboard (exercises the
real tokenizer; works mid-session).

- `SOURCE` — the `.bas` file.
- `--run` — type `RUN` afterwards.

JSON: `{"typed", "run"}`. Machine state preserved.

---

## Loading and running

### `pet load`

Load a `.prg` on the running PET via VICE autostart.

- `PRG` — the program file.
- `--run / --no-run` (default `--run`) — whether to RUN after loading.
- `--symbols PATH` — register a VICE label file for symbolic debugging.

JSON: `{"loaded", "run", "symbols"}`. Machine left running.

### `pet run`

Build/tokenize `SOURCE` as needed, then load and RUN it. `.bas` is tokenized,
`.s` is assembled (its labels are registered on the session automatically),
`.prg` is loaded directly.

- `SOURCE` — a `.bas`, `.s`, or `.prg` file.

JSON: `{"source", "prg", "symbols"}`. Machine left running.

---

## Disk images

### `pet disk create`

Create a blank disk image.

- `IMAGE` — output path; the extension picks the type (`.d64`/`.d80`/`.d82`).
- `--label TEXT` (default `disk`).
- `--id NN` (default `00`).

JSON: `{"image", "label"}`.

### `pet disk ls`

List a disk image's directory.

- `IMAGE` — the image file. JSON: `{"label", "files": [...], "blocks_free"}`.

### `pet disk put`

Copy a host file onto a disk image.

- `IMAGE` — the image file.
- `FILE` — the host file.
- `NAME` (optional) — the CBM filename (defaults to the source stem, lowercased).

JSON: `{"image", "name"}`.

### `pet disk get`

Copy a file off a disk image to the host.

- `IMAGE` — the image file.
- `NAME` — the CBM filename.
- `DEST` (optional) — output path (defaults to `NAME.prg`).

JSON: `{"image", "name", "dest"}`.

### `pet disk boot`

Attach an image to the running PET and LOAD+RUN its first file.

- `IMAGE` — the image file. JSON: `{"booted": PATH}`. Machine left running.

---

## ROM tools

ROM tooling reads ROM bytes from *your* running emulator; nothing
Commodore-copyrighted is shipped with pet-tools.

### `pet rom info`

Identify the loaded ROM set (names + content hashes).
JSON: `{"basic", "kernal", "editor", "hashes": {...}}`. Machine state preserved.

### `pet rom disasm`

Disassemble live memory with ROM + session symbol annotations.

- `START` — address or symbol (e.g. `CHROUT`).
- `LENGTH` (default `32`) — bytes to disassemble.

JSON: `{"start", "length", "lines": [...]}`. Machine state preserved.

---

## Test runner

### `pet test run`

Run one declarative YAML test. The runner boots its own fresh session
(headless + warp), loads the program, executes the steps fail-fast, and
reports pass/fail per step — capturing the screen at the point of failure.

- `YAML_FILE` — the test file.

The format:

```yaml
name: hello-world          # optional; defaults to the file name
machine: pet4032           # optional; any pet model
program: hello.bas         # .bas/.s/.prg, path relative to this file;
                           #   built/tokenized as needed
autorun: true              # default true: load and RUN. false = load only
                           #   (then drive it yourself with key steps)
timeout: 30                # default per-step timeout, seconds
steps:
  - wait:   { text: "READY." }              # screen text appears
  - key:    "run\n"                         # type keys (\n = RETURN)
  - wait:   { text: "HELLO", timeout: 5 }   # per-step timeout override
  - wait:   { mem: "$1000", equals: 42 }    # byte reaches a value
  - until:  { ref: mainloop, count: 3 }     # frame-step to a label; the
                                            #   machine STAYS stopped there
  - poke:   { addr: "$97", values: [68] }   # write bytes (state-preserving)
  - assert: { screen: "READY." }            # substring on screen now
  - assert: { mem: "@12,20", equals: 81 }   # screen cell row 12, col 20
  - assert: { mem: "$8000", equals_text: "HELLO" }  # screen RAM as text
  - assert: { mem: "$1000", equals: [1, 2, 3] }     # exact bytes
  - assert: { reg: pc, in_range: ["$C000", "$E000"] }
  - assert: { reg: a, equals: "$2A" }
```

Step kinds: `wait` (poll until true or timeout — fails the test on
timeout), `key` (feed keyboard input), `assert` (check once, now),
`poke` (write bytes; `value:` or `values:`), and `until` (run to `ref`
`count` times via a checkpoint and leave the machine stopped there —
deterministic frame stepping; fails on timeout with the reached count).
A `poke` right before an `until` is the held-key protocol (`pet key
hold` as steps). Step addresses accept everything the CLI does —
`$hex`/`0xhex`/decimal, symbols from the built program's label file,
`symbol+offset`, and `@row,col`.

JSON: `{"passed", "tests": [<report>]}`. Exit 1 if the test fails.

### `pet test programs`

Run every example-program directory (one with an `expect.txt`) as a generated
test.

- `DIRECTORY` (default `tests/programs`).

JSON: `{"passed", "tests": [...]}`. Exit 1 if any program fails.
