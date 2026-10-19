# Square: Seiken Densetsu 3's

Square's driver in Seiken Densetsu 3 and Bahamut Lagoon (the two share
0.45 of their driver code), named for its first game here. It shares none
with Secret of Mana's ([secret-of-mana.md](secret-of-mana.md)), though
Seiken Densetsu 3 is that game's sequel and has its composer.

## Games

<!-- generated: games -->
| Game | Composer (as the tags credit) | Songs (scored) |
|---|---|---|
| Bahamut Lagoon | Noriko Matsueda | 36 (36) |
| Seiken Densetsu 3 | Hiroki Kikuta | 79 (79) |
<!-- end generated -->

## What the driver does

<!-- generated: traits -->
| Trait | Measured |
|---|---|
| Clock | 96 Hz, on its ticks (19 songs); 83 Hz, on its ticks (11); 89 Hz, on its ticks (6) |
| Envelopes | ADSR at key-on: 100 % of notes; rewritten as they sound: 0 % (0.0 writes a note) |
| Pitch writes | 0.0 a note (90 %: 0.9) |
| Pitch modulation | in 8 of 115 songs |
| Noise | in 2 of 115 songs |
| Echo | 80 ms, feedback 0.44 (79 songs); 96 ms, feedback 0.62 (10); 112 ms, feedback 0.62 (7); 128 ms, feedback 0.62 (4) |
| Echo volume | 0.28 (79 songs); 0.16 (36) |
| Echo sides inverted | in 0 of 115 songs |
| Echo filter at DC | 1.09 (79 songs); 0.99 (36) |
| Master volume | 64 (115 songs) |
| Density | 761 notes in a song's first minute; a note 0.15 s |
<!-- end generated -->

- **Clock**: a timer set per song (83 to 96 Hz), key-ons on its ticks;
  modules run on it where IT can keep pace (96 Hz), else 100 rows a second.
- **Envelopes**: the instrument's ADSR at key-on, left alone.
- **Pitch**: hardly any pitch writes; pitch modulation in 8 songs, noise
  in 2.
- **Echo**: Seiken Densetsu 3's 80 ms at 0.44 through a filter that boosts
  a little (1.09 at DC), Bahamut Lagoon's 96 to 128 ms at 0.62. The echo
  volume is negative on both sides and the master negative on the left, so
  the echo is with the notes on the left and against them on the right.

## Scores

<!-- generated: scores -->
| Songs | Contour, median (10 %) | Gap dB, median (90 %) | Level, median (10-90 %) | Voice tone, median (10 %) |
|---|---|---|---|---|
| 115 | 0.94 (0.74) | 0.52 (1.13) | 1.00 (0.96-1.05) | 1.00 (0.99) |
<!-- end generated -->

## The converter

Echo repeats with their sign against the note, on each side (the
driver's median contour from 0.87 to 0.94), and between rows (Bahamut
Lagoon's 128 ms echo on held notes came out 1.4 times too strong).

## For generation

A long echo with strong feedback (Bahamut Lagoon's), widened by its signs:
with the notes on one side, against them on the other.

## Open

- Jingles and sound effects: Gate (2.3 dB off), Bahamut Lagoon Arutairu
  (2.2), Pihyara Flute (at 1.4 of its level); the treasure sparkles (Open
  Chest, Treasure!) play their sample at three times its rate in notes
  shorter than two rows ([known limits](README.md#known-limits)).
