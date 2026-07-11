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
- **Numbers.** Address and value arguments accept `$hex` (e.g. `$8000`),
  `0xhex`, or decimal. Where a label file is registered on the session (via
  `pet build`/`pet run` of assembly, or `pet load --symbols`), a **symbol
  name** is accepted anywhere an address is.
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

---

## Screen

### `pet screen`

Show the emulated screen. With no option, prints the screen decoded to text —
the preferred way to observe program output. With `--png` it writes an image.

- `--png PATH` — save a PNG screenshot instead of printing text.

JSON (text): `{"text", "rows": [...]}`. JSON (`--png`): `{"png", "width",
"height"}`. Machine state preserved.

---

## Keyboard

### `pet key type`

Type text into the running PET's keyboard buffer (`\n` = RETURN). Use it to
answer `INPUT` prompts, steer games, or drive menus; for typing in whole
programs prefer `pet basic type`.

- `TEXT` — the keystrokes (letters are case-folded to the PET's convention).

JSON: `{"typed_chars"}`. Machine state preserved.

---

## Memory

### `pet mem read`

Read emulated memory and print a hex dump (16 bytes/line with an ASCII column).

- `ADDR` — start address (`$hex`/`0x`/decimal/symbol).
- `LENGTH` (default `256`) — number of bytes.

JSON: `{"addr", "length", "hex"}` (`hex` is the bytes hex-encoded). Machine
state preserved.

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

### `pet watch add`

Set a watchpoint on a memory range (default: both load and store).

- `REF` — address or symbol.
- `--load` — break on reads.
- `--store` — break on writes.
- `--length N` (default `1`) — number of bytes to watch.

JSON: `{"id", "address", "length", "op"}`. Machine state preserved.

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
  (see the cookbook's frame-stepping recipe).
- `--timeout SECS` (default `30`).

JSON: `{"registers", "pc_symbol", "stopped": true, "count"}`. Exit 1 on
timeout (the error reports how many arrivals were reached); after a timeout
the machine is left running and the checkpoint is removed.

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
- `--model MODEL` (default `pet4032`) — selects the BASIC load address.

The recipient needs only stock VICE: `xpet game.d64` (or `xpet game.prg`)
autostarts it, and from inside the emulator `LOAD"NAME",8` then `RUN` works
the traditional way. No ROMs or pet-tools ship in the artifact.

JSON: `{"prg", "image", "title", "run"}` — `run` is the exact command to
hand to the recipient; `image` is `null` for `.prg`-only output.

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
  - assert: { screen: "READY." }            # substring on screen now
  - assert: { mem: "$8000", equals_text: "HELLO" }  # screen RAM as text
  - assert: { mem: "$1000", equals: [1, 2, 3] }     # exact bytes
  - assert: { reg: pc, in_range: ["$C000", "$E000"] }
  - assert: { reg: a, equals: "$2A" }
```

Step kinds: `wait` (poll until true or timeout — fails the test on
timeout), `key` (feed keyboard input), `assert` (check once, now).
Addresses and values accept `$hex`/`0xhex`/decimal.

JSON: `{"passed", "tests": [<report>]}`. Exit 1 if the test fails.

### `pet test programs`

Run every example-program directory (one with an `expect.txt`) as a generated
test.

- `DIRECTORY` (default `tests/programs`).

JSON: `{"passed", "tests": [...]}`. Exit 1 if any program fails.
