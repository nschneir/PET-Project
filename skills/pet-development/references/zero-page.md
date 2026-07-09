# Zero page and low memory (BASIC 4.0 / 2.0)

The BASIC memory-management pointer chain (all little-endian word pairs).
Verified live on xpet (see tests/test_docs_memory.py):

| Addr  | Name   | Meaning                                   |
|-------|--------|-------------------------------------------|
| 28/29 | TXTTAB | Start of BASIC text (= $0401)             |
| 2A/2B | VARTAB | End of program / start of variables       |
| 2C/2D | ARYTAB | Start of arrays                           |
| 2E/2F | STREND | End of arrays (start of free memory)      |
| 30/31 | FRETOP | Bottom of string storage (grows downward) |

Ordering invariant: TXTTAB <= VARTAB <= ARYTAB <= STREND <= FRETOP.

Low memory (BASIC 2.0/4.0): keyboard buffer $026F-$0278 (10 chars).
BASIC 1.0 (pet2001) differs in zero-page layout — verify with
`pet mem read` before relying on these addresses there.

Confirm anything else empirically before relying on it:
`pet mem read '$28' 10` while a known program is loaded.
