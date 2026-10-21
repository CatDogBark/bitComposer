# Phase 4: the writing

Planned in outline (2026-10-20); the detail is written when the phase
begins. See `../IDIOM.md`.

## Goal

The generator writes for SNES packs from the tables, one part at a time,
each slice judged on fidelity and on variety before the next is begun; the
chip and Genesis palettes unchanged.

## Starts from

The score of voices and the back end (phase 2); the tables and the format
2 pack (phase 3); the current writing, replaced slice by slice behind the
same `compose_song`.

## Work, provisionally

In this order, each slice written from its table with the song's seed:

1. Values and the grid (sixteenths, triplets, notes cut short).
2. The bass (figures through passing tones to the next root).
3. The harmony (parts on few chords, the pendulum, the cadence at the
   loop).
4. The melody's phrases (mostly new, the peak early, detached, the end note
   held).
5. The drums per song (a song's few figures, kept).
6. The counter-line, and the tune passing between voices.
7. Form and length (70 s once through, the parts that come back, the
   loop).
8. Voicing and spread.

Each slice is judged before the next: measured (held-out measures, the
nearest game, variety); a substitution test (that part alone in a
converted song, listened to); a blind pair; the tune-copy check in the
suite. The measures are recorded here per slice.

## Produces

New writing modules behind `compose_song`, chosen by the pack's format;
the measures per slice; a listening set per slice.

## Exit criteria

- Songs written with FFVI's vocabulary fall nearest FFVI more often than
  any other game, and with another game's, nearest it.
- Their spread over twenty seeds within the game's own spread, and each
  song committed to its figures.
- The blind pick rate recorded over versions.
- No four-bar phrase matches a game's.
- The built-in SNES packs' move decided.

## Open questions

- How much of the old writing survives: the forms, the energy curves, the
  intro conventions, the ending styles.
- How seeds stay stable across slices, so a song a listener kept can be
  made again.
- When a slice is good enough to move on: the measure, or the ear, or
  both.
- Whether a song's "situation" (a battle, a town, a scene) is a weight the
  pack carries, and where it would come from.
