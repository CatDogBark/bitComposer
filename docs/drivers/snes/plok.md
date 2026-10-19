# Plok's

The driver of Plok and Uniracers, named for its first game here. The two
share 0.58 of their driver code (`spc_check.py family`), though different
studios made them (Software Creations, and DMA Design).

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Plok | Geoff & Tim Follin | 20 (20) |
| Uniracers | Colin Anderson | 10 (10) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 320 Hz, on its ticks (4 songs); 356 Hz, on its ticks (3); 251 Hz, on its ticks (2) |
| Envelopes | ADSR at key-on: 0 % of notes; rewritten as they sound: 98 % (8.4 writes a note) |
| Pitch writes | 1.7 a note (90 %: 11.0) |
| Pitch modulation | in 0 of 30 songs |
| Noise | in 0 of 30 songs |
| Echo | 0 ms, feedback 0.0 (30 songs) |
| Echo volume | 0.0 (30 songs) |
| Echo sides inverted | in 0 of 30 songs |
| Echo filter at DC | 0.99 (30 songs) |
| Master volume | 127 (30 songs) |
| Density | 1281 notes in a song's first minute; a note 0.14 s |
<!-- end generated -->

- **Clock**: a timer set per song (251 to 356 Hz), key-ons on its ticks:
  the tempo is the timer. Faster than IT can run, so modules use 100 rows a
  second.
- **Envelopes**: written by the driver as each note sounds (GAIN, 8.4 writes
  a note), not the instrument's ADSR.
- **Echo**: none, in any song.
- **Density**: 1277 notes in a song's first minute, a note 0.14 s.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 30 | 0.98 (0.87) | 0.31 (0.48) | 1.00 (0.98-1.00) | 0.99 (0.97) |
<!-- end generated -->

## The converter

The envelopes carried whole in the volume column, as for Secret of
Evermore's.

## For generation

Dry and fast, the envelope shaped note by note by the driver; no echo
to hide in.

## Open

- Uniracers' 3rd Race (4.2 dB off, at 0.63 of its level): its loudest voices
  need IT volume 125 under a master at full, past what the global volume
  can make up ([known limits](README.md#known-limits)).
