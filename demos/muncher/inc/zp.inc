; zp.inc — Ms. Muncher: zero-page use, hardware addresses, constants.
; Glyph and key constants are DISCOVERED (Task 1), not guessed; until then
; only values proven by the invaders demo on the same model appear here.

; --- hardware / ROM-maintained ---
JIFFLO  = $8F                   ; jiffy clock low byte (60 Hz)
KEYDOWN = $97                   ; PETSCII of key held right now ($FF = none)
SCREEN  = $8000                 ; 40x25 screen RAM

SND_ACR = $E84B                 ; $10 = shift register free-runs under T2
SND_SR  = $E84A                 ; shifted bit pattern (timbre)
SND_T2  = $E848                 ; shift period = pitch (0 = silent)

; --- zero-page scratch (same cells invaders used safely on the 4032) ---
PTR     = $FB                   ; pointer: plot target
PTR2    = $FD                   ; pointer: data source

; --- screen layout (spec §3) ---
MAZE_W    = 28                  ; maze columns 0-27
MAZE_H    = 25                  ; all rows
HUD_COL   = 29                  ; HUD panel columns 29-39 (28 = gutter)
