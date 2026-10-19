# SNES drivers

The SNES plays music on its sound unit: the SNES sound CPU (SPC700) runs
the game's music driver, and the driver tells the SNES chip (S-DSP) what to
play, eight voices of BRR samples with an echo. An SPC file is a snapshot of
that unit; the emulator runs the driver from it, and the converter turns
what the driver writes to the SNES chip into an IT module (`../../SPC-IMPORT.md`).

Numbers are from 2026-10-19: all 258 songs of the games in
[the index](../README.md#games), the converter as of the SNES-chip fidelity
work (interpolation, envelope clock, echo, endings).

## Scores by driver

<!-- generated: scores -->
| Driver | Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|---|
| [Capcom](capcom.md) | 35 | 0.94 (0.61) | 0.48 (0.95) | 0.99 (0.88-1.01) | 1.00 (0.99) |
| [Square Soft US: Secret of Evermore's](secret-of-evermore.md) | 70 | 0.93 (0.52) | 0.63 (1.31) | 0.99 (0.92-1.02) | 0.99 (0.97) |
| [Square: AKAO](akao.md) | 79 | 0.98 (0.93) | 0.40 (0.74) | 0.99 (0.95-1.02) | 1.00 (0.99) |
| [Square: Secret of Mana's](secret-of-mana.md) | 68 | 0.93 (0.72) | 0.76 (1.43) | 0.97 (0.92-1.03) | 0.99 (0.97) |
| **All** | 252 | 0.95 (0.76) | 0.58 (1.22) | 0.99 (0.93-1.02) | 0.99 (0.98) |
<!-- end generated -->

Voice tone is over the voices that carry at least 5 % of their song's
loudest voice. A low tenth percentile of contour with a small gap is steady
sounds (wind beds, ambience) that match. Songs near-silent in their first
30 s (sound effects) are not scored.

## What the converter carries

The SNES chip's behaviours the converter carries, and the driver that
exposed each (`../../SPC-IMPORT.md` has the details):

| Behaviour | Found in |
|---|---|
| Samples by the addresses read at key-on | [Secret of Evermore's](secret-of-evermore.md) |
| Envelopes rewritten while a note sounds, in the volume column | [Capcom](capcom.md), [Secret of Evermore's](secret-of-evermore.md) |
| Envelope steps on the shared rate counter | [Secret of Evermore's](secret-of-evermore.md) |
| Volumes side for side, the master volume as global volume | [Secret of Mana's](secret-of-mana.md) (played at half its level before) |
| The Gaussian interpolation's softness, in the samples | [Secret of Evermore's](secret-of-evermore.md) |
| The hardware's noise, held at its clock | [AKAO](akao.md), [Secret of Evermore's](secret-of-evermore.md) |
| Pitch modulation, kept as played | [AKAO](akao.md), [Secret of Mana's](secret-of-mana.md) |
| The echo: coloured repeats until -30 dB, past the master volume, the filter's span each trip | [Capcom](capcom.md), [AKAO](akao.md) |
| A song's end: the tag's length and fade | [AKAO](akao.md) |

## Known limits

- **Held tones on echo delays that miss whole rows** (Mana's 176 ms): the
  repeats stack or cancel by chance. IT places notes no finer than a tick,
  and players round their ticks differently.
- **Samples played faster than the output rate**: the SNES chip aliases
  them (nothing filters them), libopenmpt filters; such a voice loses that
  energy (a hi-hat in Evermore's Regal Castle; some FFVI voices' top octave).
- **IT's volume ceiling**: a voice needing more than 64 is held at 64 (in
  the songs checked, at most 0.3 % of notes: Evermore's Southern Jungle).
- **The noise generator's position** is not in an SPC file: noise matches in
  level and colour, not sample for sample.

## The style packs against the drivers in play

The four built-in style packs (`bitcomposer/packs/`) were measured from these
games' SPC files before the emulator existed: their habits come from the
SNES chip's registers as each snapshot left them. Played, the drivers set
the SNES chip as they go, and some habits are not what the snapshots
showed. Each difference found is listed here, for when a pack is re-measured
or made by the importer; the packs themselves are unchanged (they are what
the generator plays, and a change to one is a change to the songs).

| Pack | Habit | The pack's notes (snapshot registers) | Measured in play |
|---|---|---|---|
| `ffvi` | echo feedback | 0.64 in every snapshot | chosen per song: 0.78 in 42 songs, 0.55 in 27, 0.62 in 7, 0.47 to 0.77 in the rest |
| `ffvi` | echo against the main | (not stated) | the master volume (63) halves the voices and not the echo, so the echo (0.20) is about 0.4 of the main |
| `mana` | echo feedback and delay | 0.31 on average; delays 32 to 176 ms, 96 and 176 the most common | two kinds of echo, not one: short and dry (48 ms in 15 songs, 96 ms in 11, no feedback) or long and ringing (176 ms with 0.72 to 0.79 in 16, 96 ms with 0.81 in 4) |
| `mana` | echo level | 0.34 of the main | 0.5 in 43 songs, 0.25 in 14, against a full master volume |
| `mana` | echo sides | the same sign in 60 of 69 | the same sign in every song |
| `evermore` | echo | off in 47 of 72; where on, an eighth of the main ("the space is in the samples, not in the echo") | on in 60 of 72 (80 ms, feedback 0.16 in 58), at 0.39 of the main |
| `evermore` | envelopes | per voice: each recipe's swell and decay | per note: the driver writes every note's envelope as it sounds (9.5 writes a note, GAIN ramps and holds), so the swells are the composer's, not the samples' |
| `megamanx` | echo | 48 ms, feedback 0.53, sides inverted | the same, in every song; the echo at 0.56 against a master of 92, about 0.8 of the main |
| `megamanx` | articulation | (not stated) | every note released by a GAIN fade a moment before the next: staccato from the driver, not the samples |
| `megamanx` | arrangement | (not stated) | the melody doubled by a delayed copy on another voice, panned the other way (Spark Mandrill: 0.12 s behind) |

## Adding a game

1. Its `.spc` files in a folder of their own beside the others (the folder is
   the game's name in the results).
2. Its entry in `drivers.json` beside the folders: `{"<folder>": {"driver":
   "<driver file>", "game": "<its name>"}}`, the driver file being one here
   (`akao`, `capcom`, ...) where the game uses a known family, so its results
   pool with the others, or a new name for a new one; `"composer"` when the
   tags' credit is cut off or wrong and a fuller one is known for sure.
3. `tools/spc_check.py traits`, `sweep`, then `doc` (CONTRIBUTING.md): the
   measured tables here, in the driver files and in [the index](../README.md#games)
   are rewritten; a new driver family gets a file whose hand-written parts are
   marked to write.
4. By hand: the driver file's notes on what the numbers mean, the converter,
   generation and anything the sweep found to its Open; a new SNES chip
   behaviour to the tables above; a pack's habit contradicted to the packs
   table.
