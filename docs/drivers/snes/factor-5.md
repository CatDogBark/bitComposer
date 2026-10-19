# Factor 5

Factor 5's sound driver, in Super Turrican 2.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Super Turrican 2 | Chris Hülsbeck | 34 (34) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 62 Hz, on its ticks (34 songs) |
| Envelopes | ADSR at key-on: 0 % of notes; rewritten as they sound: 100 % (2.4 writes a note) |
| Pitch writes | 4.4 a note (90 %: 15.5) |
| Pitch modulation | in 0 of 34 songs |
| Noise | in 0 of 34 songs |
| Echo | 32 ms, feedback -1.0 (34 songs) |
| Echo volume | 0.5 (34 songs) |
| Echo sides inverted | in 0 of 34 songs |
| Echo filter at DC | 0.75 (34 songs) |
| Master volume | 127 (34 songs) |
| Density | 634 notes in a song's first minute; a note 0.21 s |
<!-- end generated -->

- **Clock**: 62.5 Hz (a timer of 128), key-ons on its ticks. IT cannot run
  it exactly (62.4 rows a second, a tenth of a second behind over a song),
  so modules use 100 rows a second.
- **Notes**: keys a voice off and on in one go: KOFF, then KON, then KOFF
  cleared half a sample later, which the SNES chip plays as a new note.
- **Samples**: each note's directory entry written just before it, the
  one-shots looped onto a silent block.
- **Envelopes**: written by the driver (GAIN, no ADSR): a fast rise at
  key-on, a slow linear fade, a fast fade just before the next note.
- **Echo**: set (32 ms, feedback -1.0, volume 0.5) and sent to by no voice.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 34 | 0.98 (0.94) | 0.31 (0.57) | 0.99 (0.98-1.01) | 1.00 (0.99) |
<!-- end generated -->

## The converter

Every song converted silent until a key-on under KOFF counted when KOFF
clears before the SNES chip's next poll (Welcome now at a contour of 0.98,
0.5 dB off); rows on the driver's clock lost the beat over a song until the
converter checked that IT keeps pace (Braindead's contour from 0.65 to 0.99).

## For generation

Dry, the envelope the driver's: a fast rise, a slow fade, a cut just before
the next note.

## Open

- Submerged: 1.9 dB off, at 1.29 of its level.
