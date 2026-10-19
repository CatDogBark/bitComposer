# Rendering Ranger R2's

The driver of Rendering Ranger R2, named for its game here. It shares
nothing with Factor 5's in Super Turrican 2 ([factor-5.md](factor-5.md)).

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Rendering Ranger R2 | "Stefan Kramer, Jesper "Jo" Olsen" (cut off) | 19 (19) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 62 Hz, on its ticks (12 songs); 62 Hz, key-ons anywhere in a tick (6); none found (1) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 100 % (2.9 writes a note) |
| Pitch writes | 4.3 a note (90 %: 14.4) |
| Pitch modulation | in 0 of 19 songs |
| Noise | in 0 of 19 songs |
| Echo | 0 ms, feedback 0.0 (19 songs) |
| Echo volume | 0.0 (19 songs) |
| Echo sides inverted | in 0 of 19 songs |
| Echo filter at DC | 0.99 (19 songs) |
| Master volume | 127 (19 songs) |
| Density | 1091 notes in a song's first minute; a note 0.21 s |
<!-- end generated -->

- **Clock**: 62.5 Hz (a timer of 128), key-ons on its ticks in most songs:
  IT cannot run it exactly, so modules use 100 rows a second.
- **Envelopes**: ADSR at key-on, rewritten as notes sound (2.9 writes a
  note), switching to GAIN fades.
- **Samples**: single-cycle synth waveforms (32 frames, looped), swept in
  pitch (4.3 pitch writes a note).
- **Echo**: none, in any song; the master at full.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 19 | 0.95 (0.81) | 0.43 (0.67) | 1.00 (0.97-1.03) | 1.00 (0.98) |
<!-- end generated -->

## The converter

Its envelope writes showed a fault in the simulation: two writes in one
sample, sorted by their values, let a stale fastest fade win, and the Virgin
logo's notes were cut half a second early (one voice 52 dB off). They keep
their order now.

## For generation

Dry synth voices, the envelope and the pitch moving through each note.

## Open

Nothing found yet.
