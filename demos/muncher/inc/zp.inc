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

; --- glyphs (screen codes), DISCOVERED on the 4032 charset ---
; evidence: evidence/charset-zoom2.png (grid) + the half-block fusion test
; recorded in evidence/keys.md. Reverse video = code+128.
G_SPACE   = 32
G_BALL    = 81                  ; ● Ms. Muncher / energizer
G_RING    = 87                  ; ○ frightened ghost
G_HEART   = 83                  ; ♥ cutscenes
G_DIAMOND = 90                  ; ♦ fruit: strawberry
G_CLUB    = 88                  ; fruit: pear
G_SPADE   = 65                  ; fruit: apple
G_HALF_L  = 97                  ; ▌ left half block
G_HALF_R  = 225                 ; ▐ (reverse of 97) — fuses with 97 across cells
G_HALF_B  = 98                  ; ▄ bottom half block
G_HALF_T  = 226                 ; ▀ (reverse of 98) — fuses with 98 across rows
G_ARC_UL  = 85                  ; ╭ maze wall corners (rounded, arcade-like)
G_ARC_UR  = 73                  ; ╮
G_ARC_LL  = 74                  ; ╰
G_ARC_LR  = 75                  ; ╯
G_HLINE   = 64                  ; ─ wall run
G_VLINE   = 93                  ; │ wall run
G_CORN_UL = 112                 ; ┌ sharp corner family (alt wall style)
G_CORN_UR = 110                 ; ┐
G_CORN_LL = 109                 ; └
G_CORN_LR = 122                 ; ┘
G_TEE_R   = 107                 ; ├
G_TEE_L   = 115                 ; ┤
G_TEE_D   = 114                 ; ┬
G_TEE_U   = 113                 ; ┴
G_CROSS   = 91                  ; ┼
G_CHECK   = 102                 ; ▒ checkerboard (wall fill style)
G_SOLID   = 160                 ; █ reverse space (wall fill style)
G_DOT     = 46                  ; . maze dot ('.' sits low; visual check T3)
G_QUOTE   = 34                  ; " ghost eyes returning home

; --- key-down values at $97 on the 4032 (decoded PETSCII; ONE key at a
; time — ROM single-key rollover, fine for four-way steering) ---
K_W  = $57
K_A  = $41
K_S  = $53
K_D  = $44
K_SP = $20
K_1  = $31                      ; hidden: play Act 1 from title
K_2  = $32                      ; hidden: play Act 2
K_3  = $33                      ; hidden: play Act 3
