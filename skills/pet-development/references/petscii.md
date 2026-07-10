# PET text encodings: ASCII, PETSCII, screen codes

The PET uses three distinct byte encodings. The ground-truth conversion tables
live in `petlib.text` (`ascii_to_petscii`, `screen_code_to_char`); this doc
describes them.

## The three encodings

- **ASCII** — host files and the CLI.
- **PETSCII** — the keyboard and ROM I/O routines (CHROUT/CHRIN). RETURN is
  `$0D`; letters use ASCII-uppercase codes.
- **Screen codes** — the bytes actually stored in screen RAM at `$8000`. These
  are **not** PETSCII.

`pet screen` decodes screen RAM to text automatically. `pet mem read '$8000'`
shows the raw screen codes.

## Screen-code table (uppercase/graphics set)

| Codes  | Characters                                             |
|--------|--------------------------------------------------------|
| 0      | `@`                                                    |
| 1–26   | `A`–`Z`                                                |
| 27–31  | `[` `\` `]` up-arrow left-arrow                         |
| 32–63  | matches ASCII `$20`–`$3F` (space, punctuation, digits) |
| 64–127 | graphics characters                                    |

Bit 7 (`+128`) means **reverse video**; strip it before decoding (screen code
`$81` is a reverse-video `A`, i.e. the same glyph as `1`).

The low 32 letters/symbols spell out, in order:
`@ABCDEFGHIJKLMNOPQRSTUVWXYZ[\]` then up-arrow and left-arrow.

## PETSCII for keyboard input

When feeding the keyboard (as `pet basic type` and `pet key` do), text is
converted to PETSCII: `\n` → `$0D` (RETURN), letters → ASCII uppercase. Writing
lowercase source is the norm because lowercase ASCII → unshifted PETSCII, which
shows as uppercase on screen.
